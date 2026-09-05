"""
Unit tests for agents/skeptic.py.
Mocks graph.llm.generate_structured to test skeptic_node offline — no real LLM call.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from agents.skeptic import skeptic_node
from graph.state import (
    Claim,
    IdeaBrief,
    JudgedClaim,
    LaneArchetype,
    LaneFindings,
    ResearchLane,
    SkepticReport,
    Source,
    Stage,
    Verdict,
)


@pytest.fixture
def sample_state():
    return {
        "run_id": "run_test_skeptic",
        "brief": IdeaBrief(
            niche="AI PII redaction gateway",
            audience="Enterprise CTOs",
            core_question="Is there demand for an enterprise PII redaction proxy?",
        ),
        "lanes": [
            ResearchLane(
                lane_id="competitors",
                name="Competitors",
                question="Who are the top competitors?",
                archetype=LaneArchetype.COMPETITORS,
            ),
            ResearchLane(
                lane_id="customer_pain",
                name="Customer Pain",
                question="Do enterprises struggle with PII leakage today?",
                archetype=LaneArchetype.CUSTOMER_PAIN,
            ),
        ],
        "findings": [
            LaneFindings(
                lane_id="competitors",
                lane_name="Competitors",
                claims=[
                    Claim(
                        claim_id="comp-1",
                        lane_id="competitors",
                        text="Competitor X charges $99/mo",
                        sources=[Source(url="https://example.com/x", title="X pricing")],
                        unsourced=False,
                    ),
                    Claim(
                        claim_id="comp-2",
                        lane_id="competitors",
                        text="Everyone loves AI redaction tools",
                        sources=[],
                        unsourced=True,
                    ),
                ],
            ),
            LaneFindings(
                lane_id="customer_pain",
                lane_name="Customer Pain",
                claims=[
                    Claim(
                        claim_id="pain-1",
                        lane_id="customer_pain",
                        text="One forum post says PII leaks are a top concern",
                        sources=[Source(url=None, note="forum thread, unverified")],
                        unsourced=True,
                    ),
                ],
            ),
        ],
    }


def _mock_report():
    return SkepticReport(
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
                    text="Everyone loves AI redaction tools",
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
    )


@patch("agents.skeptic.generate_structured")
def test_skeptic_node_all_three_verdicts_round_trip(mock_gen, sample_state):
    mock_gen.return_value = _mock_report()

    result = skeptic_node(sample_state)

    report = result["skeptic_report"]
    verdicts = {j.claim.claim_id: j.verdict for j in report.judged}
    assert verdicts["comp-1"] == Verdict.SURVIVES
    assert verdicts["comp-2"] == Verdict.KILLED
    assert verdicts["pain-1"] == Verdict.SURVIVES_WITH_CAVEAT


@patch("agents.skeptic.generate_structured")
def test_skeptic_node_caveat_presence(mock_gen, sample_state):
    mock_gen.return_value = _mock_report()

    result = skeptic_node(sample_state)
    report = result["skeptic_report"]

    by_id = {j.claim.claim_id: j for j in report.judged}
    assert by_id["pain-1"].caveat == "Single unverified forum post, not independently confirmed."
    assert by_id["comp-1"].caveat is None
    assert by_id["comp-2"].caveat is None
    # reason is required on every verdict, not just kills
    assert by_id["comp-1"].reason
    assert by_id["comp-2"].reason
    assert by_id["pain-1"].reason


@patch("agents.skeptic.generate_structured")
def test_skeptic_node_gaps_pass_through(mock_gen, sample_state):
    mock_gen.return_value = _mock_report()

    result = skeptic_node(sample_state)
    report = result["skeptic_report"]

    assert report.gaps == ["Distribution lane question was never covered by any lane."]


@patch("agents.skeptic.generate_structured")
def test_skeptic_node_all_killed_returned_as_is(mock_gen, sample_state):
    all_killed = SkepticReport(
        judged=[
            JudgedClaim(
                claim=Claim(claim_id="c1", lane_id="competitors", text="Claim 1"),
                verdict=Verdict.KILLED,
                reason="No credible source.",
            ),
            JudgedClaim(
                claim=Claim(claim_id="c2", lane_id="customer_pain", text="Claim 2"),
                verdict=Verdict.KILLED,
                reason="Contradicted by another lane.",
            ),
        ],
        gaps=["Nothing in this run held up to scrutiny."],
    )
    mock_gen.return_value = all_killed

    result = skeptic_node(sample_state)
    report = result["skeptic_report"]

    # Not softened, not emptied, not converted — returned exactly as the model judged.
    assert len(report.judged) == 2
    assert all(j.verdict == Verdict.KILLED for j in report.judged)
    assert report.gaps == ["Nothing in this run held up to scrutiny."]


@patch("agents.skeptic.generate_structured")
def test_skeptic_node_events_single_item_list(mock_gen, sample_state):
    mock_gen.return_value = _mock_report()

    result = skeptic_node(sample_state)

    assert len(result["events"]) == 1


@patch("agents.skeptic.generate_structured")
def test_skeptic_node_return_shape(mock_gen, sample_state):
    mock_gen.return_value = _mock_report()

    result = skeptic_node(sample_state)

    assert set(result.keys()) == {"skeptic_report", "stage", "events"}
    assert result["stage"] == Stage.MERGE
