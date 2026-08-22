"""
Unit tests for tools/run_logger.py.
Tests round-trip event logging, append-only guarantees, run summary, and the track context manager.
"""
from __future__ import annotations

from pathlib import Path
import pytest

from graph.state import AgentEvent, Stage
from tools.run_logger import log_event, read_run, summarize_run, track, LOGS_DIR


@pytest.fixture(autouse=True)
def clean_logs():
    # Clean up test log files before/after tests
    run_id = "test_run_123"
    log_path = LOGS_DIR / f"{run_id}.jsonl"
    if log_path.exists():
        log_path.unlink()
    yield
    if log_path.exists():
        log_path.unlink()


def test_round_trip_and_append_only():
    run_id = "test_run_123"
    event1 = AgentEvent(
        run_id=run_id,
        agent="TestAgent1",
        stage=Stage.PLAN,
        input_summary="Input 1",
        output_summary="Output 1",
        started_at="2026-08-22T10:00:00Z",
        duration_ms=150,
        ok=True,
    )
    event2 = AgentEvent(
        run_id=run_id,
        agent="TestAgent2",
        stage=Stage.RESEARCH,
        input_summary="Input 2",
        output_summary="Output 2",
        started_at="2026-08-22T10:00:01Z",
        duration_ms=300,
        ok=True,
    )

    log_event(event1)
    events_after_1 = read_run(run_id)
    assert len(events_after_1) == 1
    assert events_after_1[0].agent == "TestAgent1"

    # Append second event — assert append-only behavior (first event preserved)
    log_event(event2)
    events_after_2 = read_run(run_id)
    assert len(events_after_2) == 2
    assert events_after_2[0].agent == "TestAgent1"
    assert events_after_2[1].agent == "TestAgent2"


def test_summarize_run():
    run_id = "test_run_123"
    event = AgentEvent(
        run_id=run_id,
        agent="Research",
        stage=Stage.RESEARCH,
        input_summary="Researching market",
        output_summary="Found 3 competitors",
        started_at="2026-08-22T10:00:00Z",
        duration_ms=500,
        ok=True,
        token_cost_usd=0.0025,
    )
    log_event(event)

    summary = summarize_run(run_id)
    assert "test_run_123" in summary
    assert "Research" in summary
    assert "$0.0025" in summary
    assert "SUCCESS" in summary


def test_track_context_manager_success():
    run_id = "test_run_123"
    with track(run_id=run_id, agent="Intake", stage=Stage.INTAKE, input_summary="User greeting") as holder:
        holder.output_summary = "Greeted user successfully"
        holder.token_cost_usd = 0.001

    events = read_run(run_id)
    assert len(events) == 1
    ev = events[0]
    assert ev.ok is True
    assert ev.agent == "Intake"
    assert ev.output_summary == "Greeted user successfully"
    assert ev.token_cost_usd == 0.001
    assert ev.duration_ms >= 0


def test_track_context_manager_exception():
    run_id = "test_run_123"
    with pytest.raises(ValueError, match="Simulated tool failure"):
        with track(run_id=run_id, agent="Research", stage=Stage.RESEARCH, input_summary="Failing step"):
            raise ValueError("Simulated tool failure")

    events = read_run(run_id)
    assert len(events) == 1
    ev = events[0]
    assert ev.ok is False
    assert ev.error == "Simulated tool failure"
    assert "ERROR: Simulated tool failure" in ev.output_summary
