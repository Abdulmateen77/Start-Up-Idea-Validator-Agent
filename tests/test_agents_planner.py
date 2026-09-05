"""
Unit tests for agents/planner.py.
Mocks graph.llm.generate_structured to test plan_node wiring offline — no live LLM.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from agents.planner import plan_node
from graph.state import IdeaBrief, LaneArchetype, ResearchLane, ResearchPlan, Stage


@pytest.fixture
def sample_brief():
    return IdeaBrief(
        niche="AI PII redaction gateway",
        audience="Enterprise CTOs at Series B+ SaaS companies",
        core_question="Is there demand for an enterprise PII redaction proxy?",
    )


def make_state(brief):
    return {"run_id": "run_test_planner", "brief": brief}


TWO_LANE_PLAN = ResearchPlan(
    lanes=[
        ResearchLane(
            lane_id="customer_pain",
            name="Customer Pain",
            question="How do enterprise CTOs currently handle PII redaction before shipping logs to third parties?",
            archetype=LaneArchetype.CUSTOMER_PAIN,
        ),
        ResearchLane(
            lane_id="competitors",
            name="Competitors",
            question="Which vendors already sell PII redaction proxies to enterprises, and what do they charge?",
            archetype=LaneArchetype.COMPETITORS,
        ),
    ]
)

FIVE_LANE_PLAN = ResearchPlan(
    lanes=[
        ResearchLane(
            lane_id="customer_pain",
            name="Customer Pain",
            question="What incidents have pushed enterprise CTOs to look for PII redaction tooling?",
            archetype=LaneArchetype.CUSTOMER_PAIN,
        ),
        ResearchLane(
            lane_id="competitors",
            name="Competitors",
            question="Which vendors sell PII redaction proxies today, and what do they charge?",
            archetype=LaneArchetype.COMPETITORS,
        ),
        ResearchLane(
            lane_id="distribution",
            name="Distribution",
            question="What channels reach security/compliance buyers at Series B+ SaaS companies?",
            archetype=LaneArchetype.DISTRIBUTION,
        ),
        ResearchLane(
            lane_id="regulatory",
            name="Regulatory",
            question="What compliance regimes (GDPR, HIPAA, SOC 2) require PII redaction at this audience's scale?",
            archetype=LaneArchetype.REGULATORY,
        ),
        ResearchLane(
            lane_id="build_vs_buy",
            name="Build vs Buy Sentiment",
            question="How do engineering leaders discuss building this in-house vs buying, in public forums?",
            archetype=LaneArchetype.OTHER,
        ),
    ]
)


@patch("agents.planner.generate_structured")
def test_plan_node_returns_exact_keys(mock_gen, sample_brief, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mock_gen.return_value = TWO_LANE_PLAN

    result = plan_node(make_state(sample_brief))

    assert set(result.keys()) == {"lanes", "stage", "events"}


@patch("agents.planner.generate_structured")
def test_plan_node_events_is_single_item_list(mock_gen, sample_brief, tmp_path, monkeypatch):
    # This is the check that catches the "read holder.event inside the with-block"
    # bug — it must be read after track()'s finally clause runs.
    monkeypatch.chdir(tmp_path)
    mock_gen.return_value = TWO_LANE_PLAN

    result = plan_node(make_state(sample_brief))

    assert len(result["events"]) == 1
    assert result["stage"] == Stage.RESEARCH


@pytest.mark.parametrize("plan", [TWO_LANE_PLAN, FIVE_LANE_PLAN])
@patch("agents.planner.generate_structured")
def test_plan_node_handles_variable_lane_counts(mock_gen, plan, sample_brief, tmp_path, monkeypatch):
    # No special-casing on lane count: 2 lanes and 5 lanes must both pass through
    # untouched.
    monkeypatch.chdir(tmp_path)
    mock_gen.return_value = plan

    result = plan_node(make_state(sample_brief))

    assert result["lanes"] == plan.lanes
    assert len(result["lanes"]) == len(plan.lanes)
    assert len(result["events"]) == 1


@patch("agents.planner.generate_structured")
def test_plan_node_other_archetype_passes_through_untouched(mock_gen, sample_brief, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    mock_gen.return_value = FIVE_LANE_PLAN

    result = plan_node(make_state(sample_brief))

    other_lanes = [lane for lane in result["lanes"] if lane.archetype == LaneArchetype.OTHER]
    assert len(other_lanes) == 1
    assert other_lanes[0].lane_id == "build_vs_buy"
    assert other_lanes[0].question == FIVE_LANE_PLAN.lanes[-1].question
