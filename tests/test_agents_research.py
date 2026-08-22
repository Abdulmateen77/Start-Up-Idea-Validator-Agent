"""
Unit tests for agents/research.py.
Mocks graph.llm.generate_structured and Firecrawl client to test research_node execution offline.
"""
from __future__ import annotations

from unittest.mock import patch
import pytest

from agents.research import research_node
from graph.state import IdeaBrief, LaneArchetype, ResearchLane, LaneTask, Claim, Source
from tools.errors import SearchError


@pytest.fixture
def sample_task():
    return LaneTask(
        run_id="run_test_research",
        lane=ResearchLane(
            lane_id="competitors",
            name="Competitors",
            question="Who are the top competitors in AI PII redaction?",
            archetype=LaneArchetype.COMPETITORS,
        ),
        brief=IdeaBrief(
            niche="AI PII redaction gateway",
            audience="Enterprise CTOs",
            core_question="Is there demand for an enterprise PII redaction proxy?",
        ),
    )


@patch("agents.research.generate_structured")
@patch("agents.research.scrape")
@patch("agents.research.search")
def test_research_node_happy_path(mock_search, mock_scrape, mock_gen_struct, sample_task):
    from tools.firecrawl_client import SearchHit, ScrapedPage

    mock_search.return_value = [
        SearchHit(url="https://example.com/comp1", title="Comp 1", description="Redaction tool")
    ]
    mock_scrape.return_value = ScrapedPage(
        url="https://example.com/comp1", title="Comp 1", markdown="Pricing: $99/mo"
    )

    from agents.research import ExtractionResult, ExtractedClaim
    mock_gen_struct.return_value = ExtractionResult(
        claims=[
            ExtractedClaim(
                claim_id="comp-1",
                text="Competitor 1 charges $99/mo for PII redaction",
                source_url="https://example.com/comp1",
                source_title="Comp 1",
                unsourced=False,
            )
        ]
    )

    result = research_node(sample_task)

    assert "findings" in result
    assert "events" in result
    assert len(result["findings"]) == 1
    findings = result["findings"][0]
    assert findings.lane_id == "competitors"
    assert findings.no_evidence_found is False
    assert len(findings.claims) == 1
    assert findings.claims[0].text == "Competitor 1 charges $99/mo for PII redaction"
    assert not findings.claims[0].unsourced
    assert len(result["events"]) == 1


@patch("agents.research.search")
def test_research_node_no_evidence_found(mock_search, sample_task):
    mock_search.return_value = []

    result = research_node(sample_task)

    findings = result["findings"][0]
    assert findings.no_evidence_found is True
    assert len(findings.claims) == 0


@patch("agents.research.search")
def test_research_node_tool_failure(mock_search, sample_task):
    mock_search.side_effect = SearchError("API rate limit exceeded")

    result = research_node(sample_task)

    findings = result["findings"][0]
    assert len(findings.tool_failures) > 0
    assert "API rate limit exceeded" in findings.tool_failures[0].error
    assert findings.no_evidence_found is True


@patch("agents.research.generate_structured")
@patch("agents.research.scrape")
@patch("agents.research.search")
def test_research_node_archetype_other(mock_search, mock_scrape, mock_gen_struct, sample_task):
    # Test that OTHER archetype (generic fallback) works successfully
    sample_task["lane"].archetype = LaneArchetype.OTHER
    sample_task["lane"].lane_id = "other_lane"
    sample_task["lane"].name = "Other Lane"

    from tools.firecrawl_client import SearchHit, ScrapedPage
    mock_search.return_value = [SearchHit(url="https://example.com/other", title="Other", description="Info")]
    mock_scrape.return_value = ScrapedPage(url="https://example.com/other", title="Other", markdown="General info")

    from agents.research import ExtractionResult, ExtractedClaim
    mock_gen_struct.return_value = ExtractionResult(
        claims=[
            ExtractedClaim(
                claim_id="other-1",
                text="General finding in other lane",
                source_url="https://example.com/other",
                source_title="Other",
            )
        ]
    )

    result = research_node(sample_task)
    findings = result["findings"][0]
    assert findings.lane_id == "other_lane"
    assert len(findings.claims) == 1
    assert findings.claims[0].text == "General finding in other lane"
    assert findings.no_evidence_found is False
