"""
Projection from LangGraph state to the frozen wire format. OWNERSHIP: Lead only.

Spec: docs/API_CONTRACT.md — the frontend is built against that document, so any
change here that isn't reflected there is a break.

The important job of this module is deriving `status`. The frontend must never have
to work out whether a run is paused on a human, so we read the pending interrupt off
the graph snapshot and say so explicitly, along with what is being asked.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from graph.state import (
    HumanDecision,
    IdeaBrief,
    IntakeTurn,
    LaneArchetype,
    NextMove,
    Recommendation,
    ResearchLane,
    Stage,
)

Status = Literal["running", "awaiting_human", "done", "failed"]


class LaneProgress(BaseModel):
    lane_id: str
    name: str
    archetype: LaneArchetype
    state: Literal["pending", "running", "done", "failed"]
    claim_count: int = 0
    no_evidence_found: bool = False
    had_tool_failure: bool = False


class RunSummary(BaseModel):
    run_id: str
    status: Status
    stage: Stage
    raw_idea: str
    created_at: str
    updated_at: str


class RunView(BaseModel):
    run_id: str
    status: Status
    stage: Stage
    raw_idea: str
    created_at: str
    updated_at: str
    awaiting: dict[str, Any] | None = None
    brief: IdeaBrief | None = None
    intake_turns: list[IntakeTurn] = []
    lanes: list[ResearchLane] = []
    lane_progress: list[LaneProgress] = []
    recommendation: Recommendation | None = None
    human_decision: HumanDecision | None = None
    error: str | None = None


def pending_interrupt(snapshot: Any) -> dict | None:
    """
    The payload of the interrupt the graph is currently blocked on, if any.

    Our two interrupt nodes emit dicts already tagged with `kind`
    ("intake_question" / "gate_decision"), so this needs no interpretation — which is
    the point. Interpretation would mean the server guessing, and the contract says
    the server *knows*.
    """
    for task in getattr(snapshot, "tasks", ()) or ():
        for intr in getattr(task, "interrupts", ()) or ():
            value = getattr(intr, "value", None)
            if isinstance(value, dict):
                return value
    return None


def derive_status(snapshot: Any, state: dict) -> Status:
    if state.get("stage") == Stage.FAILED or state.get("error"):
        return "failed"
    if pending_interrupt(snapshot) is not None:
        return "awaiting_human"
    # No next node means the graph ran to completion.
    if not getattr(snapshot, "next", None):
        return "done"
    return "running"


def lane_progress(state: dict) -> list[LaneProgress]:
    """
    Per-lane view of the parallel fan-out.

    `no_evidence_found` and `had_tool_failure` stay distinct all the way to the wire:
    the first is a legitimate result, the second is a problem, and collapsing them
    would discard exactly the signal Skeptic depends on downstream.
    """
    findings = {f.lane_id: f for f in (state.get("findings") or [])}
    stage = state.get("stage")
    out: list[LaneProgress] = []

    for lane in state.get("lanes") or []:
        found = findings.get(lane.lane_id)
        if found is None:
            lane_state = "running" if stage == Stage.RESEARCH else "pending"
            out.append(
                LaneProgress(
                    lane_id=lane.lane_id,
                    name=lane.name,
                    archetype=lane.archetype,
                    state=lane_state,
                )
            )
            continue

        broke = bool(found.tool_failures)
        # A lane that failed its tools AND produced nothing did not "find no
        # evidence" — it never got to look. Report that honestly.
        failed = broke and not found.claims and not found.no_evidence_found
        out.append(
            LaneProgress(
                lane_id=lane.lane_id,
                name=lane.name,
                archetype=lane.archetype,
                state="failed" if failed else "done",
                claim_count=len(found.claims),
                no_evidence_found=found.no_evidence_found,
                had_tool_failure=broke,
            )
        )
    return out


def to_run_view(snapshot: Any, state: dict, record: dict) -> RunView:
    """Assemble the wire object. `record` is the api.store row."""
    status = derive_status(snapshot, state)
    awaiting = pending_interrupt(snapshot) if status == "awaiting_human" else None

    return RunView(
        run_id=record["run_id"],
        status=status,
        stage=state.get("stage") or Stage.INTAKE,
        raw_idea=record["raw_idea"],
        created_at=record["created_at"],
        updated_at=record["updated_at"],
        awaiting=awaiting,
        brief=state.get("brief"),
        intake_turns=state.get("intake_turns") or [],
        lanes=state.get("lanes") or [],
        lane_progress=lane_progress(state),
        recommendation=state.get("recommendation"),
        human_decision=state.get("human_decision"),
        error=state.get("error"),
    )


def to_summary(view: RunView) -> RunSummary:
    return RunSummary(
        run_id=view.run_id,
        status=view.status,
        stage=view.stage,
        raw_idea=view.raw_idea,
        created_at=view.created_at,
        updated_at=view.updated_at,
    )
