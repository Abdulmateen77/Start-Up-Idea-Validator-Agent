"""
Append-only run logger and context manager for Supervisor monitoring.
Writes AgentEvent audit trails to logs/<run_id>.jsonl.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Generator

from graph.state import AgentEvent, Stage

LOGS_DIR = Path("logs")


def _get_log_path(run_id: str) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    # Sanitize run_id to prevent path traversal
    safe_run_id = "".join(c for c in run_id if c.isalnum() or c in ("-", "_"))
    return LOGS_DIR / f"{safe_run_id}.jsonl"


def log_event(event: AgentEvent) -> None:
    """
    Append an AgentEvent to the run's JSONL log file.
    Append-only: never truncates or rewrites existing records.
    """
    log_path = _get_log_path(event.run_id)
    event_dict = event.model_dump()
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event_dict) + "\n")


def read_run(run_id: str) -> list[AgentEvent]:
    """
    Read all AgentEvents for a given run from its JSONL log file.
    Returns an empty list if no log file exists.
    """
    log_path = _get_log_path(run_id)
    if not log_path.exists():
        return []

    events: list[AgentEvent] = []
    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                events.append(AgentEvent.model_validate(data))
            except Exception:
                # Skip malformed lines gracefully
                continue
    return events


def summarize_run(run_id: str) -> str:
    """
    Generate a human-readable summary of a run from its recorded events.
    """
    events = read_run(run_id)
    if not events:
        return f"Run {run_id}: No events recorded."

    total_duration_ms = sum(e.duration_ms for e in events)
    total_cost = sum(e.token_cost_usd for e in events if e.token_cost_usd is not None)
    failed_events = [e for e in events if not e.ok]

    lines = [
        f"=== Run Summary: {run_id} ===",
        f"Total Events: {len(events)}",
        f"Total Duration: {total_duration_ms / 1000.0:.2f}s",
        f"Total Token Cost: ${total_cost:.4f}",
        f"Status: {'FAILED (' + str(len(failed_events)) + ' errors)' if failed_events else 'SUCCESS'}",
        "",
        "Timeline:",
    ]

    for e in events:
        status_str = "OK" if e.ok else f"FAIL ({e.error})"
        lines.append(
            f"  [{e.started_at}] Stage: {e.stage.value} | Agent: {e.agent} | {status_str} ({e.duration_ms}ms)"
            f"\n    In: {e.input_summary}"
            f"\n    Out: {e.output_summary}"
        )

    return "\n".join(lines)


@contextmanager
def track(
    run_id: str, agent: str, stage: Stage, input_summary: str
) -> Generator[Any, None, None]:
    """
    Context manager to time code blocks, build an AgentEvent, log it, and re-raise on exception.
    Yields a holder object where caller can set `output_summary` and `token_cost_usd`.
    """
    start_time = datetime.now(timezone.utc)
    started_at = start_time.isoformat()

    class Holder:
        def __init__(self) -> None:
            self.output_summary: str = ""
            self.token_cost_usd: float | None = None
            self.event: AgentEvent | None = None

    holder = Holder()
    ok = True
    error_msg: str | None = None

    try:
        yield holder
    except Exception as e:
        ok = False
        error_msg = str(e)
        raise
    finally:
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        output_summary = holder.output_summary
        if not ok and not output_summary:
            output_summary = f"ERROR: {error_msg}"

        event = AgentEvent(
            run_id=run_id,
            agent=agent,
            stage=stage,
            input_summary=input_summary,
            output_summary=output_summary,
            started_at=started_at,
            duration_ms=duration_ms,
            ok=ok,
            error=error_msg,
            token_cost_usd=holder.token_cost_usd,
        )
        holder.event = event
        log_event(event)
