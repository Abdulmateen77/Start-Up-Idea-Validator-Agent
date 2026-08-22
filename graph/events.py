"""
Building AgentEvents. OWNERSHIP: Lead only.

Deliberately split from `tools/run_logger.py` (Hermes): this module *constructs*
events, that one *persists* them. Nodes shouldn't hand-roll timestamps and duration
maths, and the Supervisor shouldn't care who built the event it's writing.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from datetime import datetime, timezone

from graph.state import AgentEvent, Stage


@contextmanager
def timed_event(run_id: str, agent: str, stage: Stage, input_summary: str):
    """
    Time a node and yield a mutable slot for its result.

        with timed_event(run_id, "intake", Stage.INTAKE, brief_in) as ev:
            ...
            ev["output_summary"] = "asked a follow-up"
        return {"events": [ev["event"]], ...}

    On exception the event is recorded with ok=False and the error attached, then the
    exception is re-raised — a node must never look successful because it crashed.
    """
    started = datetime.now(timezone.utc).isoformat()
    t0 = time.perf_counter()
    slot: dict = {"output_summary": "", "cost": None}

    def _build(ok: bool, error: str | None) -> AgentEvent:
        return AgentEvent(
            run_id=run_id,
            agent=agent,
            stage=stage,
            input_summary=_clip(input_summary),
            output_summary=_clip(slot["output_summary"]),
            started_at=started,
            duration_ms=int((time.perf_counter() - t0) * 1000),
            ok=ok,
            error=error,
            token_cost_usd=slot["cost"],
        )

    try:
        yield slot
    except Exception as exc:
        slot["event"] = _build(ok=False, error=f"{type(exc).__name__}: {exc}")
        raise
    else:
        slot["event"] = _build(ok=True, error=None)


def _clip(text: str, limit: int = 400) -> str:
    """Summaries are for humans scanning a log, not a second copy of the payload."""
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"
