"""
Integration tests for the FastAPI layer (api/main.py). OWNERSHIP: test-file only.

Drives the REAL LangGraph pipeline (all real nodes wired via graph/build.py) through
the REAL HTTP API. Only the LLM (graph.llm.generate_structured / converse_structured,
patched at each node module's import site) and Firecrawl (tools.firecrawl_client.search
/ scrape, patched at agents.research's import site) are mocked — no live network, no
live LLM, anywhere.

Spec: docs/API_CONTRACT.md. Reference for driving the compiled graph:
tests/test_graph_wiring.py.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# CRITICAL: IVA_DB must be pointed at a throwaway file BEFORE api.main (or
# anything importing graph.build / api.store) is imported anywhere in this
# process — both modules read os.getenv("IVA_DB", ...) at import time.
# ---------------------------------------------------------------------------
import os
import tempfile

_tmp_db_fd, _tmp_db_path = tempfile.mkstemp(suffix=".sqlite")
os.close(_tmp_db_fd)
os.environ["IVA_DB"] = _tmp_db_path

from contextlib import ExitStack  # noqa: E402
from unittest.mock import MagicMock, patch  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from agents.human_gate import NextMoveMenu  # noqa: E402
from agents.intake import IntakeReply  # noqa: E402
from agents.research import ExtractedClaim, ExtractionResult  # noqa: E402
from api.main import app  # noqa: E402
from graph.llm import Generated  # noqa: E402
from graph.state import (  # noqa: E402
    Claim,
    FindingGroup,
    IdeaBrief,
    JudgedClaim,
    LaneArchetype,
    NextMove,
    Recommendation,
    ResearchLane,
    ResearchPlan,
    SkepticReport,
    Source,
    Verdict,
)
from tools.errors import ScrapeError
from tools.firecrawl_client import ScrapedPage, SearchHit


# ---------------------------------------------------------------------------
# Cleanup: remove the temp sqlite file (and its -shm/-wal siblings) once the
# whole module is done, so the repo is left exactly as it was found.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def _cleanup_tmp_db():
    yield
    for suffix in ("", "-shm", "-wal", "-journal"):
        path = _tmp_db_path + suffix
        if os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # agents/research.py and agents/*.py write AgentEvent logs to a relative
    # ./logs/ dir via tools/run_logger.py (LOGS_DIR = Path("logs")). Run each
    # test from a scratch cwd so these never land in the real repo's logs/.
    monkeypatch.chdir(tmp_path)
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Shared fixtures for driving the pipeline
# ---------------------------------------------------------------------------

BRIEF = IdeaBrief(
    niche="AI bookkeeping for solo Shopify sellers",
    audience="Solo Shopify store owners doing $10-100k/mo",
    core_question="Should we build automated bookkeeping software for small Shopify sellers?",
)

LANES = [
    ResearchLane(
        lane_id="customer_pain",
        name="Customer Pain",
        question="Do solo Shopify sellers struggle with bookkeeping today?",
        archetype=LaneArchetype.CUSTOMER_PAIN,
    ),
    ResearchLane(
        lane_id="competitors",
        name="Competitors",
        question="Who already sells bookkeeping automation to Shopify sellers, and what do they charge?",
        archetype=LaneArchetype.COMPETITORS,
    ),
]

SURVIVING_CLAIM_TEXT = "Solo sellers report spending 5+ hours/month on manual reconciliation."
KILLED_CLAIM_TEXT = "Competitor Y charges $500/mo with no automation."


def _intake_mock(num_questions: int = 2, brief: IdeaBrief = BRIEF) -> MagicMock:
    """
    `num_questions` not-ready turns, then one ready turn carrying the brief —
    matching how agents/intake.py's IntakeReply loop behaves for real.
    """
    replies = [
        Generated(
            value=IntakeReply(ready=False, question=f"Question {i + 1}?", brief=None),
            interaction_id=f"interaction-{i + 1}",
        )
        for i in range(num_questions)
    ]
    replies.append(
        Generated(
            value=IntakeReply(ready=True, question=None, brief=brief),
            interaction_id="interaction-final",
        )
    )
    return MagicMock(side_effect=replies)


def _planner_mock(lanes: list[ResearchLane] = LANES) -> MagicMock:
    return MagicMock(return_value=ResearchPlan(lanes=list(lanes)))


def _research_success_mocks():
    """search/scrape/generate_structured mocks that give every lane real evidence."""
    search_mock = MagicMock(
        return_value=[
            SearchHit(
                url="https://example.com/evidence",
                title="Evidence",
                description="Some evidence snippet",
            )
        ]
    )
    scrape_mock = MagicMock(
        return_value=ScrapedPage(
            url="https://example.com/evidence",
            title="Evidence",
            markdown="Solo sellers spend hours a month reconciling Shopify payouts by hand.",
        )
    )
    extraction_mock = MagicMock(
        return_value=ExtractionResult(
            claims=[
                ExtractedClaim(
                    claim_id="",
                    text="A generic evidence-backed finding",
                    source_url="https://example.com/evidence",
                    source_title="Evidence",
                    unsourced=False,
                )
            ]
        )
    )
    return search_mock, scrape_mock, extraction_mock


def _skeptic_mock() -> MagicMock:
    report = SkepticReport(
        judged=[
            JudgedClaim(
                claim=Claim(
                    claim_id="pain-1",
                    lane_id="customer_pain",
                    text=SURVIVING_CLAIM_TEXT,
                    sources=[Source(url="https://example.com/evidence", title="Evidence")],
                ),
                verdict=Verdict.SURVIVES,
                reason="Corroborated by multiple independent sources.",
            ),
            JudgedClaim(
                claim=Claim(
                    claim_id="comp-1",
                    lane_id="competitors",
                    text=KILLED_CLAIM_TEXT,
                    sources=[],
                    unsourced=True,
                ),
                verdict=Verdict.KILLED,
                reason="Single unverified claim with no supporting source.",
            ),
        ],
        gaps=["Distribution channel viability was never directly tested."],
    )
    return MagicMock(return_value=report)


def _merge_mock() -> MagicMock:
    """
    Returns a canned Recommendation, but ALSO asserts (a real check, not just
    presence in the output) that the killed claim's text never reached the
    prompt merge_node builds — proving merge_node's own filtering ran for real
    and didn't just happen to produce a clean-looking response.
    """

    def _fake_generate(prompt, schema, **kwargs):
        assert KILLED_CLAIM_TEXT not in prompt, "killed claim leaked into the merge prompt"
        assert SURVIVING_CLAIM_TEXT in prompt, "surviving claim should reach the merge prompt"
        return Recommendation(
            core_question=BRIEF.core_question,
            findings=[FindingGroup(lane_name="Customer Pain", points=[SURVIVING_CLAIM_TEXT])],
            gaps=["Distribution channel viability was never directly tested."],
            verdict="Promising signal on pain, but distribution is untested.",
        )

    return MagicMock(side_effect=_fake_generate)


def _gate_mock() -> MagicMock:
    menu = NextMoveMenu(
        moves=[
            NextMove(
                move_id="customer_interviews",
                label="Talk to 5 solo Shopify sellers",
                rationale="Direct evidence is the fastest way to close the distribution gap.",
            ),
            NextMove(
                move_id="pass",
                label="Pass on this idea",
                rationale="The evidence doesn't yet justify further investment.",
            ),
        ]
    )
    return MagicMock(return_value=menu)


def _full_pipeline_patches(num_questions: int = 2):
    """
    ExitStack of every patch needed to drive raw idea -> gate decision through the
    REAL graph. Caller enters it, drives the HTTP calls, then exits it.
    """
    search_mock, scrape_mock, extraction_mock = _research_success_mocks()
    stack = ExitStack()
    stack.enter_context(patch("agents.intake.converse_structured", _intake_mock(num_questions)))
    stack.enter_context(patch("agents.planner.generate_structured", _planner_mock()))
    stack.enter_context(patch("agents.research.search", search_mock))
    stack.enter_context(patch("agents.research.scrape", scrape_mock))
    stack.enter_context(patch("agents.research.generate_structured", extraction_mock))
    stack.enter_context(patch("agents.skeptic.generate_structured", _skeptic_mock()))
    stack.enter_context(patch("agents.merge.generate_structured", _merge_mock()))
    stack.enter_context(patch("agents.human_gate.generate_structured", _gate_mock()))
    return stack


def _drive_to_gate(client: TestClient, num_questions: int = 2) -> dict:
    """POST /runs, then answer every intake question until the run reaches the gate."""
    resp = client.post("/runs", json={"raw_idea": "Should we build AI bookkeeping for Shopify?"})
    assert resp.status_code == 201
    view = resp.json()

    for _ in range(num_questions):
        assert view["status"] == "awaiting_human"
        assert view["awaiting"]["kind"] == "intake_question"
        resp = client.post(
            f"/runs/{view['run_id']}/respond",
            json={"kind": "intake_answer", "message": "a concrete answer"},
        )
        assert resp.status_code == 200
        view = resp.json()

    assert view["status"] == "awaiting_human", view
    assert view["awaiting"]["kind"] == "gate_decision", view
    return view


# ---------------------------------------------------------------------------
# 1. POST /runs happy path
# ---------------------------------------------------------------------------


def test_create_run_happy_path(client):
    with patch("agents.intake.converse_structured", _intake_mock(2)):
        resp = client.post("/runs", json={"raw_idea": "Should we build AI bookkeeping for Shopify?"})

    assert resp.status_code == 201
    view = resp.json()

    for key in (
        "run_id", "status", "stage", "raw_idea", "created_at", "updated_at",
        "awaiting", "brief", "intake_turns", "lanes", "lane_progress",
        "recommendation", "human_decision", "error",
    ):
        assert key in view, f"RunView is missing '{key}' per docs/API_CONTRACT.md"

    assert view["status"] == "awaiting_human"
    assert view["stage"] == "intake"
    assert view["raw_idea"] == "Should we build AI bookkeeping for Shopify?"
    assert view["awaiting"] is not None
    assert view["awaiting"]["kind"] == "intake_question"
    assert view["awaiting"]["question"] == "Question 1?"
    assert view["brief"] is None
    assert view["error"] is None


# ---------------------------------------------------------------------------
# 2. Full intake loop through POST /runs/{id}/respond
# ---------------------------------------------------------------------------


def test_intake_loop_asks_multiple_questions_then_produces_brief(client):
    # Once the third answer lands, Intake produces a brief and the graph falls
    # straight through into Plan -> Research -> ... so those stages need real
    # (mocked) nodes too, not just Intake.
    with _full_pipeline_patches(num_questions=3):
        resp = client.post("/runs", json={"raw_idea": "bookkeeping thing"})
        assert resp.status_code == 201
        view = resp.json()
        run_id = view["run_id"]

        seen_questions = []
        for i in range(3):
            assert view["status"] == "awaiting_human"
            assert view["awaiting"]["kind"] == "intake_question"
            seen_questions.append(view["awaiting"]["question"])

            resp = client.post(
                f"/runs/{run_id}/respond",
                json={"kind": "intake_answer", "message": f"answer {i}"},
            )
            assert resp.status_code == 200
            view = resp.json()

        # Each round asked a genuinely new question, not a repeat.
        assert seen_questions == ["Question 1?", "Question 2?", "Question 3?"]
        assert len(set(seen_questions)) == 3

        # intake_turns records the whole back-and-forth for the UI.
        assert len(view["intake_turns"]) == 6  # 3 agent questions + 3 human answers

        # Brief landed; run has moved past Intake into planning/research territory.
        assert view["brief"] is not None
        assert view["brief"]["niche"] == BRIEF.niche


# ---------------------------------------------------------------------------
# 3. Full fan-out: Plan -> Research -> Skeptic -> Merge -> Human Gate
# ---------------------------------------------------------------------------


def test_full_pipeline_reaches_gate_with_clean_recommendation(client):
    with _full_pipeline_patches(num_questions=2):
        view = _drive_to_gate(client, num_questions=2)

    # Lanes from the (mocked) Planner made it all the way through.
    lane_ids = {lane["lane_id"] for lane in view["lanes"]}
    assert lane_ids == {"customer_pain", "competitors"}

    rec = view["awaiting"]["recommendation"]
    assert rec is not None
    assert rec["core_question"] == BRIEF.core_question

    # The surviving claim is present...
    all_text = rec["verdict"] + " " + " ".join(rec["gaps"])
    all_text += " " + " ".join(
        point for group in rec["findings"] for point in group["points"]
    )
    assert SURVIVING_CLAIM_TEXT in all_text

    # ...and the killed claim is nowhere in the recommendation. Not a substring
    # of the verdict, not a gap, not a finding point.
    assert KILLED_CLAIM_TEXT not in all_text

    # next_moves proposed by the (mocked) Human Gate node.
    move_ids = {m["move_id"] for m in view["awaiting"]["next_moves"]}
    assert "pass" in move_ids


# ---------------------------------------------------------------------------
# 4. GET /runs/{id} matches what POST/respond returned
# ---------------------------------------------------------------------------


def test_get_run_matches_post_response(client):
    with _full_pipeline_patches(num_questions=2):
        posted_view = _drive_to_gate(client, num_questions=2)

    fetched = client.get(f"/runs/{posted_view['run_id']}")
    assert fetched.status_code == 200
    fetched_view = fetched.json()

    assert fetched_view["status"] == posted_view["status"]
    assert fetched_view["stage"] == posted_view["stage"]
    assert fetched_view["awaiting"] == posted_view["awaiting"]
    assert fetched_view["lanes"] == posted_view["lanes"]
    assert fetched_view["lane_progress"] == posted_view["lane_progress"]
    assert fetched_view["brief"] == posted_view["brief"]


# ---------------------------------------------------------------------------
# 5. GET /runs lists runs, newest-updated first
# ---------------------------------------------------------------------------


def test_list_runs_shows_both_newest_first(client):
    with patch("agents.intake.converse_structured", _intake_mock(2)):
        r1 = client.post("/runs", json={"raw_idea": "idea one"}).json()
        r2 = client.post("/runs", json={"raw_idea": "idea two"}).json()

    listing = client.get("/runs")
    assert listing.status_code == 200
    runs = listing.json()["runs"]

    ids = [r["run_id"] for r in runs]
    assert r1["run_id"] in ids
    assert r2["run_id"] in ids

    # Newest-updated first: updated_at must be non-increasing down the list.
    timestamps = [r["updated_at"] for r in runs]
    assert timestamps == sorted(timestamps, reverse=True)

    # Summary shape matches RunSummary (no brief/recommendation/etc).
    summary = runs[0]
    assert set(summary.keys()) == {
        "run_id", "status", "stage", "raw_idea", "created_at", "updated_at",
    }


# ---------------------------------------------------------------------------
# 6. Wrong `kind` for the current pause -> 422
# ---------------------------------------------------------------------------


def test_respond_with_wrong_kind_returns_422(client):
    with patch("agents.intake.converse_structured", _intake_mock(2)):
        view = client.post("/runs", json={"raw_idea": "bookkeeping thing"}).json()

    assert view["awaiting"]["kind"] == "intake_question"

    resp = client.post(
        f"/runs/{view['run_id']}/respond",
        json={"kind": "gate_decision", "chosen_move_id": "pass"},
    )
    assert resp.status_code == 422
    assert "detail" in resp.json()


# ---------------------------------------------------------------------------
# 7. Respond when NOT awaiting_human -> 409
# ---------------------------------------------------------------------------


def test_respond_when_not_awaiting_human_returns_409(client):
    with _full_pipeline_patches(num_questions=2):
        view = _drive_to_gate(client, num_questions=2)
        run_id = view["run_id"]
        finish = client.post(
            f"/runs/{run_id}/respond",
            json={"kind": "gate_decision", "chosen_move_id": "pass"},
        )
        assert finish.status_code == 200
        assert finish.json()["status"] == "done"

        # The run is finished; nothing is awaiting_human anymore.
        again = client.post(
            f"/runs/{run_id}/respond",
            json={"kind": "gate_decision", "chosen_move_id": "pass"},
        )

    assert again.status_code == 409
    assert "detail" in again.json()


# ---------------------------------------------------------------------------
# 8. GET /runs/{missing} -> 404
# ---------------------------------------------------------------------------


def test_get_missing_run_returns_404(client):
    resp = client.get("/runs/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["detail"] == "run not found"


# ---------------------------------------------------------------------------
# 9. gate_decision chosen_move_id completes the run
# ---------------------------------------------------------------------------


def test_chosen_move_id_completes_the_run(client):
    with _full_pipeline_patches(num_questions=2):
        view = _drive_to_gate(client, num_questions=2)
        resp = client.post(
            f"/runs/{view['run_id']}/respond",
            json={"kind": "gate_decision", "chosen_move_id": "customer_interviews"},
        )

    assert resp.status_code == 200
    final = resp.json()
    assert final["status"] == "done"
    assert final["stage"] == "done"
    assert final["awaiting"] is None
    assert final["human_decision"]["chosen_move_id"] == "customer_interviews"


# ---------------------------------------------------------------------------
# 10. gate_decision rerun_lane_id sends the run backwards
# ---------------------------------------------------------------------------


def test_rerun_lane_id_sends_run_backwards(client):
    with _full_pipeline_patches(num_questions=2):
        view = _drive_to_gate(client, num_questions=2)
        lane_id = view["lanes"][0]["lane_id"]

        resp = client.post(
            f"/runs/{view['run_id']}/respond",
            json={"kind": "gate_decision", "rerun_lane_id": lane_id},
        )
        assert resp.status_code == 200
        after_rerun = resp.json()

        # rerun_lane_id sends the pipeline back through research -> skeptic ->
        # merge -> gate, so the run should be awaiting a *new* gate decision
        # rather than done.
        assert after_rerun["status"] == "awaiting_human"
        assert after_rerun["stage"] != "done"
        assert after_rerun["awaiting"]["kind"] == "gate_decision"
        assert after_rerun["human_decision"]["rerun_lane_id"] == lane_id

        # merge_findings reducer: still exactly one LaneFindings per lane, not
        # a duplicate appended for the re-run lane.
        assert len(after_rerun["lane_progress"]) == 2
        lane_ids = [lp["lane_id"] for lp in after_rerun["lane_progress"]]
        assert sorted(lane_ids) == sorted({lp["lane_id"] for lp in after_rerun["lane_progress"]})


# ---------------------------------------------------------------------------
# 11. no_evidence_found vs had_tool_failure stay distinct in lane_progress
# ---------------------------------------------------------------------------


def test_lane_progress_distinguishes_tool_failure_from_no_evidence(client):
    """
    One lane (Competitors, archetype COMPETITORS) gets search hits but every
    scrape() call raises ScrapeError -> falls back to search-snippet text, so
    it still produces a claim (no_evidence_found=False) while carrying a
    recorded ToolFailure (had_tool_failure=True).

    The other lane (Customer Pain, archetype CUSTOMER_PAIN) gets zero search
    hits -> a legitimate "nothing found" (no_evidence_found=True) with no tool
    failure at all (had_tool_failure=False).

    Distinguishing by query content works because playbook query_hints differ
    per archetype (see tools/playbooks.py) even though niche/audience/
    core_question are identical across lanes in one run.
    """

    def fake_search(query: str, limit: int = 3):
        q = query.lower()
        if any(k in q for k in ("pricing", "competitor", "alternatives", "comparison")):
            return [
                SearchHit(
                    url="https://example.com/competitor-x",
                    title="Competitor X",
                    description="Competitor X charges a monthly fee for bookkeeping automation.",
                )
            ]
        return []

    def fake_scrape(url: str):
        raise ScrapeError(f"scrape failed for {url}")

    extraction_mock = MagicMock(
        return_value=ExtractionResult(
            claims=[
                ExtractedClaim(
                    claim_id="",
                    text="Competitor X charges a monthly fee for bookkeeping automation.",
                    source_url="https://example.com/competitor-x",
                    source_title="Competitor X",
                    unsourced=False,
                )
            ]
        )
    )

    stack = ExitStack()
    stack.enter_context(patch("agents.intake.converse_structured", _intake_mock(2)))
    stack.enter_context(patch("agents.planner.generate_structured", _planner_mock()))
    stack.enter_context(patch("agents.research.search", MagicMock(side_effect=fake_search)))
    stack.enter_context(patch("agents.research.scrape", MagicMock(side_effect=fake_scrape)))
    stack.enter_context(patch("agents.research.generate_structured", extraction_mock))
    stack.enter_context(patch("agents.skeptic.generate_structured", _skeptic_mock()))
    stack.enter_context(patch("agents.merge.generate_structured", _merge_mock()))
    stack.enter_context(patch("agents.human_gate.generate_structured", _gate_mock()))

    with stack:
        view = _drive_to_gate(client, num_questions=2)

    by_id = {lp["lane_id"]: lp for lp in view["lane_progress"]}
    assert set(by_id) == {"customer_pain", "competitors"}

    tool_failure_lane = by_id["competitors"]
    no_evidence_lane = by_id["customer_pain"]

    assert tool_failure_lane["had_tool_failure"] is True
    assert tool_failure_lane["no_evidence_found"] is False

    assert no_evidence_lane["no_evidence_found"] is True
    assert no_evidence_lane["had_tool_failure"] is False

    # Not collapsed into the same booleans on either side.
    assert tool_failure_lane["had_tool_failure"] != no_evidence_lane["had_tool_failure"]
    assert tool_failure_lane["no_evidence_found"] != no_evidence_lane["no_evidence_found"]
