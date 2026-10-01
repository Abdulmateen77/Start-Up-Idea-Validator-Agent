"""
FastAPI app. OWNERSHIP: Lead only.

Spec: docs/API_CONTRACT.md. No auth anywhere — deliberate, see CLAUDE.md.

The graph runs in a background thread per advance, because a single run can spend
minutes in the Research fan-out and must not block the event loop. Callers poll
`GET /runs/{id}` (always correct) and may additionally subscribe to SSE for liveness.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from typing import Any, Literal

from dotenv import load_dotenv

# Load .env BEFORE importing anything that reads configuration, so the LLM
# provider's API key and FIRECRAWL_API_KEY are actually present in os.environ.
# Without this every run dies at the first node with a missing-credentials error even
# though .env is correct — the file is not read automatically, and the tests never
# caught it because they mock the LLM and Firecrawl entirely.
#
# Deliberately done at the entrypoint rather than inside graph/llm.py: tests must
# stay hermetic and must never silently pick up real credentials from disk.
load_dotenv()

from fastapi import FastAPI, HTTPException  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from sse_starlette.sse import EventSourceResponse  # noqa: E402

from api import store  # noqa: E402
from api.views import RunView, to_run_view, to_summary  # noqa: E402
from graph.build import build_graph, open_checkpointer  # noqa: E402
from graph.state import Stage  # noqa: E402

# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class CreateRun(BaseModel):
    raw_idea: str


class Respond(BaseModel):
    """One of the two pause replies. `kind` must match the current interrupt."""

    kind: Literal["intake_answer", "gate_decision"]
    message: str | None = None
    chosen_move_id: str | None = None
    custom_note: str | None = None
    rerun_lane_id: str | None = None


# ---------------------------------------------------------------------------
# App / graph lifecycle
# ---------------------------------------------------------------------------

_state: dict[str, Any] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # The checkpointer is a context manager holding a SQLite connection; it has to
    # outlive every request, so it's entered once for the process lifetime.
    cm = open_checkpointer()
    checkpointer = cm.__enter__()
    _state["cm"] = cm
    _state["graph"] = build_graph(checkpointer=checkpointer)
    try:
        yield
    finally:
        cm.__exit__(None, None, None)


app = FastAPI(title="Idea Validator Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("IVA_CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


def _graph():
    return _state["graph"]


def _config(run_id: str) -> dict:
    return {"configurable": {"thread_id": run_id}}


def _view(run_id: str) -> RunView:
    record = store.get_run(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="run not found")
    snapshot = _graph().get_state(_config(run_id))
    return to_run_view(snapshot, snapshot.values or {}, record)


async def _advance(run_id: str, payload: Any) -> None:
    """
    Drive the graph until it next pauses or finishes.

    Runs in a worker thread: the Research fan-out is long and blocking, and holding
    the event loop would stall every other request including SSE.
    """

    def _run() -> None:
        try:
            _graph().invoke(payload, _config(run_id))
        except Exception as exc:
            # Record the failure INTO the checkpoint. A node that raises leaves its
            # pending next-node behind, which derive_status reads as "running" — so
            # without this the client polls a dead run forever instead of being told
            # what broke. Then re-raise so the caller still gets a 500.
            _graph().update_state(
                _config(run_id),
                {"error": f"{type(exc).__name__}: {exc}", "stage": Stage.FAILED},
            )
            raise
        finally:
            store.touch_run(run_id)

    await asyncio.to_thread(_run)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/runs", status_code=201, response_model=RunView)
async def create_run(body: CreateRun) -> RunView:
    run_id = uuid.uuid4().hex
    store.create_run(run_id, body.raw_idea)

    await _advance(
        run_id,
        {
            "run_id": run_id,
            "raw_idea": body.raw_idea,
            "stage": Stage.INTAKE,
            "intake_turns": [],
            "findings": [],
            "events": [],
        },
    )
    return _view(run_id)


@app.get("/runs")
async def list_runs() -> dict:
    out = []
    for record in store.list_runs():
        snapshot = _graph().get_state(_config(record["run_id"]))
        view = to_run_view(snapshot, snapshot.values or {}, record)
        out.append(to_summary(view))
    return {"runs": out}


@app.get("/runs/{run_id}", response_model=RunView)
async def get_run(run_id: str) -> RunView:
    return _view(run_id)


@app.post("/runs/{run_id}/respond", response_model=RunView)
async def respond(run_id: str, body: Respond) -> RunView:
    view = _view(run_id)
    if view.status != "awaiting_human":
        raise HTTPException(status_code=409, detail="run is not awaiting human input")

    expected = (view.awaiting or {}).get("kind")
    wanted = "intake_question" if body.kind == "intake_answer" else "gate_decision"
    if expected != wanted:
        raise HTTPException(
            status_code=422,
            detail=f"run is awaiting '{expected}', not '{body.kind}'",
        )

    if body.kind == "intake_answer":
        if not body.message:
            raise HTTPException(status_code=422, detail="message is required")
        resume: Any = body.message
    else:
        chosen = [body.chosen_move_id, body.custom_note, body.rerun_lane_id]
        if sum(1 for c in chosen if c) != 1:
            raise HTTPException(
                status_code=422,
                detail="provide exactly one of chosen_move_id, custom_note, rerun_lane_id",
            )
        resume = {
            "chosen_move_id": body.chosen_move_id,
            "custom_note": body.custom_note,
            "rerun_lane_id": body.rerun_lane_id,
        }

    from langgraph.types import Command

    await _advance(run_id, Command(resume=resume))
    return _view(run_id)


@app.get("/runs/{run_id}/stream")
async def stream(run_id: str):
    """
    SSE liveness. Deliberately a thin diff-poller over the same projection the REST
    endpoint returns: the contract promises polling alone is always correct, so this
    must never become a second source of truth that can disagree with it.
    """

    async def gen():
        last: tuple | None = None
        while True:
            try:
                view = _view(run_id)
            except HTTPException:
                yield {"data": '{"event":"error","detail":"run not found"}'}
                return

            fingerprint = (
                view.status,
                view.stage,
                tuple((l.lane_id, l.state, l.claim_count) for l in view.lane_progress),
            )
            if fingerprint != last:
                last = fingerprint
                yield {"data": _event_json(view)}

            if view.status in ("done", "failed"):
                return
            await asyncio.sleep(1.0)

    return EventSourceResponse(gen())


def _event_json(view: RunView) -> str:
    import json

    if view.status == "awaiting_human":
        payload = {"event": "awaiting_human", "awaiting": view.awaiting}
    elif view.status == "done":
        payload = {"event": "run_completed", "run_id": view.run_id}
    elif view.status == "failed":
        payload = {"event": "error", "detail": view.error or "run failed"}
    else:
        payload = {"event": "stage_changed", "stage": view.stage}
    return json.dumps(payload, default=str)
