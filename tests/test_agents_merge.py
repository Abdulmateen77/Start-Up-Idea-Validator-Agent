"""
Unit tests for agents/merge.py.
Mocks graph.llm.generate_structured to test merge_node offline — no real LLM call.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from agents.merge import merge_node
from graph.state import (
    Claim,
    FindingGroup,
    IdeaBrief,
    JudgedClaim,
    LaneArchetype,
    Recommendation,
    ResearchLane,
    SkepticReport,
    Source,
    Stage,
    Verdict,
)


KILLED_CLAIM_TEXT = "Everyone loves AI redaction tools unconditionally"


@pytest.fixture
def sample_state():
    return {
        "run_id": "run_test_merge",
        "brief": IdeaBrief(
            niche="AI PII redaction gateway",
            audience="Enterprise CTOs",
            core_question="Is there demand for an enterprise PII redaction proxy?",
        ),
        "skeptic_report": SkepticReport(
            judged=[
                JudgedClaim(
                    claim=Claim(
                        claim_id="comp-1",
                        lane_id="competitors",
                        text="Competitor X charges $99/mo",
                        sources=[Source(url="https://example.com/x", title="X pricing")],
                        unsourced=False,
                    ),
                    verdict=Verdict.SURVIVES,
                    reason="Pricing page directly confirms this figure.",
                    caveat=None,
                ),
                JudgedClaim(
                    claim=Claim(
                        claim_id="comp-2",
                        lane_id="competitors",
                        text=KILLED_CLAIM_TEXT,
                        sources=[],
                        unsourced=True,
                    ),
                    verdict=Verdict.KILLED,
                    reason="Unsourced sweeping generalization with no supporting evidence.",
                    caveat=None,
                ),
                JudgedClaim(
                    claim=Claim(
                        claim_id="pain-1",
                        lane_id="customer_pain",
                        text="One forum post says PII leaks are a top concern",
                        sources=[Source(url=None, note="forum thread, unverified")],
                        unsourced=True,
                    ),
                    verdict=Verdict.SURVIVES_WITH_CAVEAT,
                    reason="Plausible and directionally relevant but is a single anecdote.",
                    caveat="Single unverified forum post, not independently confirmed.",
                ),
            ],
            gaps=["Distribution lane question was never covered by any lane."],
        ),
        "lanes": [
            ResearchLane(
                lane_id="competitors",
                name="Competitors",
                question="Who sells this and what do they charge?",
                archetype=LaneArchetype.COMPETITORS,
            ),
            ResearchLane(
                lane_id="customer_pain",
                name="Customer Pain",
                question="How do buyers handle this today?",
                archetype=LaneArchetype.CUSTOMER_PAIN,
            ),
        ],
    }


def _mock_recommendation():
    return Recommendation(
        core_question="Is there demand for an enterprise PII redaction proxy?",
        findings=[
            FindingGroup(
                lane_name="competitors",
                points=["Competitor X charges $99/mo"],
            ),
            FindingGroup(
                lane_name="customer_pain",
                points=[
                    "One forum post says PII leaks are a top concern "
                    "(caveat: single unverified forum post, not independently confirmed)"
                ],
            ),
        ],
        gaps=["Distribution lane question was never covered by any lane."],
        verdict="Some pricing signal exists, but customer pain evidence is thin and unverified.",
    )


@patch("agents.merge.generate_structured")
def test_merge_node_killed_claims_never_leak(mock_gen, sample_state):
    mock_gen.return_value = _mock_recommendation()

    result = merge_node(sample_state)
    recommendation = result["recommendation"]

    # The single highest-value assertion in this file: the killed claim's text must
    # not appear anywhere in the output findings/points.
    all_points_text = " ".join(
        point for group in recommendation.findings for point in group.points
    )
    assert KILLED_CLAIM_TEXT not in all_points_text
    assert KILLED_CLAIM_TEXT not in recommendation.verdict

    # And verify the prompt handed to the model never included the killed claim
    # either — Merge must not even see it, not just avoid echoing it.
    prompt_arg = mock_gen.call_args[0][0]
    assert KILLED_CLAIM_TEXT not in prompt_arg


@patch("agents.merge.generate_structured")
def test_merge_node_caveats_survive_into_points(mock_gen, sample_state):
    mock_gen.return_value = _mock_recommendation()

    result = merge_node(sample_state)
    recommendation = result["recommendation"]

    all_points_text = " ".join(
        point for group in recommendation.findings for point in group.points
    )
    assert "caveat" in all_points_text.lower()
    assert "forum post" in all_points_text.lower()


@patch("agents.merge.generate_structured")
def test_merge_node_gaps_pass_through(mock_gen, sample_state):
    mock_gen.return_value = _mock_recommendation()

    result = merge_node(sample_state)
    recommendation = result["recommendation"]

    assert recommendation.gaps == ["Distribution lane question was never covered by any lane."]


@patch("agents.merge.generate_structured")
def test_merge_node_events_single_item_list(mock_gen, sample_state):
    mock_gen.return_value = _mock_recommendation()

    result = merge_node(sample_state)

    assert len(result["events"]) == 1


@patch("agents.merge.generate_structured")
def test_merge_node_return_shape(mock_gen, sample_state):
    mock_gen.return_value = _mock_recommendation()

    result = merge_node(sample_state)

    assert set(result.keys()) == {"recommendation", "stage", "events"}
    assert result["stage"] == Stage.HUMAN_GATE


@patch("agents.merge.generate_structured")
def test_merge_node_prompt_uses_human_readable_lane_names(mock_gen, sample_state):
    # Claim only carries lane_id ("competitors"), never the human-readable
    # ResearchLane.name ("Competitors"). Without resolving it via state["lanes"],
    # the model's only cue for FindingGroup.lane_name is the raw slug.
    mock_gen.return_value = _mock_recommendation()

    merge_node(sample_state)

    prompt_arg = mock_gen.call_args[0][0]
    assert "Competitors" in prompt_arg
    assert "Customer Pain" in prompt_arg


@patch("agents.merge.generate_structured")
def test_merge_node_falls_back_to_slug_when_lane_unmatched(mock_gen, sample_state):
    # A lane_id with no entry in state["lanes"] (e.g. lanes wasn't populated) must
    # not crash — it degrades to showing the slug, not a KeyError.
    sample_state["lanes"] = []
    mock_gen.return_value = _mock_recommendation()

    result = merge_node(sample_state)

    prompt_arg = mock_gen.call_args[0][0]
    assert "competitors" in prompt_arg
    assert result["recommendation"] is not None
