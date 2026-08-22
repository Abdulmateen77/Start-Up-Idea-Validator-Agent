"""
Wiring tests for graph/build.py. OWNERSHIP: Lead only.

Every node is a fake, so this exercises the parts that are genuinely mine — the
Intake interrupt loop, the Send fan-out, the fan-in reducer, and the backwards
re-run edge — without waiting on Hermes or Antigravity, and without an LLM.
"""

from __future__ import annotations

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from graph.build import NodeRegistry, build_graph
from graph.state import (
    Claim,
    FindingGroup,
    IdeaBrief,
    JudgedClaim,
    LaneArchetype,
    LaneFindings,
    Recommendation,
    ResearchLane,
    SkepticReport,
    Stage,
    Verdict,
    merge_findings,
)

BRIEF = IdeaBrief(niche="n", audience="a", core_question="q?")

LANES = [
    ResearchLane(
        lane_id="pain", name="Customer Pain", question="p?",
        archetype=LaneArchetype.CUSTOMER_PAIN,
    ),
    ResearchLane(
        lane_id="comp", name="Competitors", question="c?",
        archetype=LaneArchetype.COMPETITORS,
    ),
    ResearchLane(
        lane_id="odd", name="Something Novel", question="o?",
        archetype=LaneArchetype.OTHER,
    ),
]


def _registry(research_calls: list, intake_questions: int = 1) -> NodeRegistry:
    def intake(state):
        # Ask `intake_questions` times, then produce the brief.
        asked = sum(1 for t in state.get("intake_turns", []) if t.role == "agent")
        answered = sum(1 for t in state.get("intake_turns", []) if t.role == "human")
        if answered >= intake_questions:
            return {"brief": BRIEF, "stage": Stage.PLAN}
        from graph.state import IntakeTurn

        return {
            "intake_turns": [
                *state.get("intake_turns", []),
                IntakeTurn(role="agent", content=f"question {asked + 1}?"),
            ],
            "stage": Stage.INTAKE,
        }

    def plan(state):
        return {"lanes": list(LANES), "stage": Stage.RESEARCH}

    def research(task):
        lane = task["lane"]
        research_calls.append(lane.lane_id)
        n = research_calls.count(lane.lane_id)
        return {
            "findings": [
                LaneFindings(
                    lane_id=lane.lane_id,
                    lane_name=lane.name,
                    claims=[
                        Claim(
                            claim_id=f"{lane.lane_id}-{n}",
                            lane_id=lane.lane_id,
                            text=f"attempt {n}",
                        )
                    ],
                )
            ]
        }

    def skeptic(state):
        judged = [
            JudgedClaim(claim=c, verdict=Verdict.SURVIVES, reason="ok")
            for f in state["findings"]
            for c in f.claims
        ]
        return {
            "skeptic_report": SkepticReport(judged=judged, gaps=["g"]),
            "stage": Stage.MERGE,
        }

    def merge(state):
        return {
            "recommendation": Recommendation(
                core_question="q?",
                findings=[FindingGroup(lane_name="Customer Pain", points=["p"])],
                gaps=["g"],
                verdict="unclear",
            ),
            "stage": Stage.HUMAN_GATE,
        }

    def human_gate(state):
        return {"next_moves": [], "stage": Stage.HUMAN_GATE}

    return NodeRegistry(
        intake=intake, plan=plan, research=research,
        skeptic=skeptic, merge=merge, human_gate=human_gate,
    )


@pytest.fixture
def app_and_calls():
    calls: list[str] = []
    app = build_graph(registry=_registry(calls), checkpointer=MemorySaver())
    return app, calls


def _start(app, run_id="r1"):
    cfg = {"configurable": {"thread_id": run_id}}
    app.invoke(
        {"run_id": run_id, "raw_idea": "vague idea",
         "stage": Stage.INTAKE, "intake_turns": [], "findings": [], "events": []},
        cfg,
    )
    return cfg


def _interrupt(app, cfg):
    snap = app.get_state(cfg)
    for task in snap.tasks:
        for intr in task.interrupts:
            return intr.value
    return None


def test_intake_pauses_and_asks(app_and_calls):
    app, _ = app_and_calls
    cfg = _start(app)

    payload = _interrupt(app, cfg)
    assert payload is not None, "graph should pause on the Intake question"
    assert payload["kind"] == "intake_question"
    assert payload["question"] == "question 1?"


def test_intake_loop_runs_until_brief_then_fans_out():
    calls: list[str] = []
    app = build_graph(
        registry=_registry(calls, intake_questions=3), checkpointer=MemorySaver()
    )
    cfg = _start(app, "loop")

    # Three questions, three answers - the loop is unbounded by design.
    for i in range(3):
        payload = _interrupt(app, cfg)
        assert payload["kind"] == "intake_question", f"round {i}"
        app.invoke(Command(resume=f"answer {i}"), cfg)

    # After the brief lands, all three lanes must have run.
    assert sorted(calls) == ["comp", "odd", "pain"]


def test_fan_out_runs_every_lane_once(app_and_calls):
    app, calls = app_and_calls
    cfg = _start(app)
    app.invoke(Command(resume="an answer"), cfg)

    assert sorted(calls) == ["comp", "odd", "pain"]
    findings = app.get_state(cfg).values["findings"]
    assert len(findings) == 3, "fan-in should collect one LaneFindings per lane"


def test_pauses_at_human_gate_with_recommendation(app_and_calls):
    app, _ = app_and_calls
    cfg = _start(app)
    app.invoke(Command(resume="an answer"), cfg)

    payload = _interrupt(app, cfg)
    assert payload["kind"] == "gate_decision"
    assert payload["recommendation"] is not None


def test_choosing_a_move_ends_the_run(app_and_calls):
    app, _ = app_and_calls
    cfg = _start(app)
    app.invoke(Command(resume="an answer"), cfg)
    app.invoke(Command(resume={"chosen_move_id": "pass"}), cfg)

    snap = app.get_state(cfg)
    assert not snap.next, "run should be finished"
    assert snap.values["human_decision"].chosen_move_id == "pass"
    assert snap.values["stage"] == Stage.DONE


def test_rerun_lane_goes_backwards_and_replaces_not_appends(app_and_calls):
    """The reducer must supersede the stale lane, or Skeptic judges both copies."""
    app, calls = app_and_calls
    cfg = _start(app)
    app.invoke(Command(resume="an answer"), cfg)
    app.invoke(Command(resume={"rerun_lane_id": "comp"}), cfg)

    # Only the requested lane re-ran.
    assert calls.count("comp") == 2
    assert calls.count("pain") == 1

    findings = app.get_state(cfg).values["findings"]
    assert len(findings) == 3, "re-run must replace the lane, not append a duplicate"
    comp = next(f for f in findings if f.lane_id == "comp")
    assert comp.claims[0].text == "attempt 2", "stale result should be superseded"


def test_merge_findings_reducer_is_last_write_wins():
    a = LaneFindings(lane_id="x", lane_name="X", claims=[])
    b = LaneFindings(lane_id="x", lane_name="X", no_evidence_found=True)
    c = LaneFindings(lane_id="y", lane_name="Y")

    assert merge_findings([], [a]) == [a]
    assert merge_findings([a], [c]) == [a, c]
    assert merge_findings([a], [b]) == [b]
    assert merge_findings(None, None) == []
