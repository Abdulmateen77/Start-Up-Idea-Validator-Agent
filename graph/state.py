"""
THE CONTRACT.

Every node's input and output shape lives here. This is the single source of truth
that lets Hermes, Antigravity, and the Lead build in parallel without colliding.

OWNERSHIP: Lead only. No other coding agent may edit this file.
If you need a field that isn't here, STOP and report to the Lead. Do not add it
yourself — a local edit here is exactly the "silent interface drift" this file exists
to prevent.

Read `briefs/RULES.md` before writing any code against this.
"""

from __future__ import annotations

import operator
from enum import Enum
from typing import Annotated, Any, TypedDict

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------


class Stage(str, Enum):
    """Where a run currently sits. Mirrors workflows/01..06."""

    INTAKE = "intake"
    PLAN = "plan"
    RESEARCH = "research"
    SKEPTIC = "skeptic"
    MERGE = "merge"
    HUMAN_GATE = "human_gate"
    DONE = "done"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Stage 1 — Intake  (workflows/01_intake_refine.md)
# ---------------------------------------------------------------------------


class IntakeTurn(BaseModel):
    """One exchange in the Intake back-and-forth."""

    role: str = Field(description="'agent' or 'human'")
    content: str


class IdeaBrief(BaseModel):
    """Intake's output. The pipeline does not proceed until this is populated."""

    niche: str = Field(description="Specific. Not 'the market', not 'businesses'.")
    audience: str = Field(description="Specific role + company size/stage.")
    core_question: str = Field(description="The single question the pipeline answers.")


# ---------------------------------------------------------------------------
# Stage 2 — Plan  (workflows/02_plan_research_lanes.md)
# ---------------------------------------------------------------------------


class LaneArchetype(str, Enum):
    """
    Which research *playbook* a lane uses — not which agent runs it.

    There is exactly ONE Research agent. This tag selects a prompt fragment and a
    preferred set of source types (see `tools/playbooks.py`), because the lanes need
    genuinely different methods: Competitors wants vendor pricing pages, Customer
    Pain wants forums and reviews, Distribution wants channel/CAC data.

    OTHER is the generic fallback and it is load-bearing — it's what keeps lanes
    open-ended. The Planner invents lanes per-idea; anything it invents that isn't
    listed here gets OTHER and still works. Adding a value here is an optimisation,
    never a precondition for a lane to exist.
    """

    CUSTOMER_PAIN = "customer_pain"
    COMPETITORS = "competitors"
    DISTRIBUTION = "distribution"
    REGULATORY = "regulatory"
    UNIT_ECONOMICS = "unit_economics"
    TECHNICAL_FEASIBILITY = "technical_feasibility"
    OTHER = "other"


class ResearchLane(BaseModel):
    """One parallel research lane. Lanes are decided per-idea, never fixed."""

    lane_id: str = Field(description="Stable slug, e.g. 'competitors'.")
    name: str = Field(description="Human-readable, e.g. 'Competitors'.")
    question: str = Field(
        description="Specific and answerable. NOT a restatement of core_question."
    )
    archetype: LaneArchetype = Field(
        default=LaneArchetype.OTHER,
        description="Selects the research playbook. OTHER when nothing fits.",
    )


class ResearchPlan(BaseModel):
    lanes: list[ResearchLane]


# ---------------------------------------------------------------------------
# Stage 3 — Research  (workflows/03_research_lane.md)
# ---------------------------------------------------------------------------


class Source(BaseModel):
    url: str | None = None
    title: str | None = None
    note: str | None = Field(
        default=None,
        description="Context when url is None, e.g. 'referenced in forum thread'.",
    )


class Claim(BaseModel):
    """A single evidence claim. `unsourced=True` is valid — Skeptic relies on it."""

    claim_id: str
    lane_id: str
    text: str
    sources: list[Source] = Field(default_factory=list)
    unsourced: bool = False


class ToolFailure(BaseModel):
    """Never swallow a tool error. Supervisor logs these. See workflows/03 edge cases."""

    tool: str
    error: str
    retried: bool = False
    recovered: bool = False


class LaneFindings(BaseModel):
    """One Research node's output. N of these fan back in via `operator.add`."""

    lane_id: str
    lane_name: str
    claims: list[Claim] = Field(default_factory=list)
    no_evidence_found: bool = Field(
        default=False,
        description="Explicit 'nothing found' is a valid finding, not a failure.",
    )
    tool_failures: list[ToolFailure] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Stage 4 — Skeptic  (workflows/04_skeptic_review.md)
# ---------------------------------------------------------------------------


class Verdict(str, Enum):
    SURVIVES = "survives"
    SURVIVES_WITH_CAVEAT = "survives_with_caveat"
    KILLED = "killed"


class JudgedClaim(BaseModel):
    claim: Claim
    verdict: Verdict
    reason: str = Field(description="One line. Required even when it survives.")
    caveat: str | None = Field(
        default=None, description="Required when verdict is SURVIVES_WITH_CAVEAT."
    )


class SkepticReport(BaseModel):
    judged: list[JudgedClaim]
    gaps: list[str] = Field(
        default_factory=list,
        description="Plan questions no lane answered credibly. Never fabricate to fill.",
    )


# ---------------------------------------------------------------------------
# Stage 5 — Merge  (workflows/05_merge_recommendation.md)
# ---------------------------------------------------------------------------


class FindingGroup(BaseModel):
    lane_name: str
    points: list[str] = Field(description="Surviving claims, caveats kept inline.")


class Recommendation(BaseModel):
    """The one-pager. Readable in under a minute."""

    core_question: str
    findings: list[FindingGroup]
    gaps: list[str] = Field(default_factory=list)
    verdict: str = Field(
        description="Plain prose. 'Not enough evidence yet' is a legitimate verdict."
    )


# ---------------------------------------------------------------------------
# Stage 6 — Human Gate  (workflows/06_human_gate.md)
# ---------------------------------------------------------------------------


class NextMove(BaseModel):
    """Tailored to what's actually uncertain. NOT a fixed menu every run."""

    move_id: str
    label: str
    rationale: str = Field(description="Why this move, given the gaps above.")


class HumanDecision(BaseModel):
    chosen_move_id: str | None = None
    custom_note: str | None = Field(
        default=None, description="Set when the human writes their own next move."
    )
    rerun_lane_id: str | None = Field(
        default=None, description="Set when the human wants a lane re-run instead."
    )


# ---------------------------------------------------------------------------
# Supervisor  (workflows/07_supervisor_monitoring.md) — cross-cutting
# ---------------------------------------------------------------------------


class AgentEvent(BaseModel):
    """Emitted by every node. Supervisor's audit trail. Append-only."""

    run_id: str
    agent: str
    stage: Stage
    input_summary: str
    output_summary: str
    started_at: str = Field(description="ISO 8601 UTC.")
    duration_ms: int
    ok: bool = True
    error: str | None = None
    token_cost_usd: float | None = None


# ---------------------------------------------------------------------------
# The graph state
# ---------------------------------------------------------------------------


class RunState(TypedDict, total=False):
    """
    LangGraph's shared state, threaded through every node.

    CRITICAL — the two `operator.add` reducers below are what make the parallel
    Research fan-out work. Nodes spawned via `Send` write concurrently; without a
    reducer LangGraph raises on the concurrent write. Do not "simplify" them to
    plain lists.

    Nodes return a PARTIAL dict (only the keys they set), never the whole state.
    """

    run_id: str
    stage: Stage

    # Intake
    raw_idea: str
    intake_turns: list[IntakeTurn]
    brief: IdeaBrief | None

    # Plan
    lanes: list[ResearchLane]

    # Research — parallel fan-in, MUST use the reducer
    findings: Annotated[list[LaneFindings], operator.add]

    # Skeptic / Merge
    skeptic_report: SkepticReport | None
    recommendation: Recommendation | None

    # Human Gate
    next_moves: list[NextMove]
    human_decision: HumanDecision | None

    # Supervisor — parallel-safe append-only log
    events: Annotated[list[AgentEvent], operator.add]


class LaneTask(TypedDict):
    """
    Payload handed to ONE Research node via LangGraph's `Send` API.

    A fanned-out Research node receives THIS, not the full RunState.
    """

    run_id: str
    lane: ResearchLane
    brief: IdeaBrief


__all__ = [
    "Stage",
    "IntakeTurn",
    "IdeaBrief",
    "LaneArchetype",
    "ResearchLane",
    "ResearchPlan",
    "Source",
    "Claim",
    "ToolFailure",
    "LaneFindings",
    "Verdict",
    "JudgedClaim",
    "SkepticReport",
    "FindingGroup",
    "Recommendation",
    "NextMove",
    "HumanDecision",
    "AgentEvent",
    "RunState",
    "LaneTask",
]
