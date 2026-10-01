"""
Human Gate — build the next-move menu. OWNERSHIP: Lead only.

Spec: workflows/06_human_gate.md

This node only *proposes* moves. Capturing the decision is `human_gate_wait_node` in
graph/build.py, and the choice itself is always the human's — the model never picks.

The menu is generated per-run from what's actually uncertain, not selected from a
fixed list. A run where Skeptic killed everything should offer different moves than
one with a confident verdict.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from graph.events import timed_event
from graph.llm import generate_structured
from graph.state import NextMove, Recommendation, RunState, Stage

SYSTEM = """\
You propose next moves after an idea-validation run. You do NOT make the decision and \
you do NOT recommend one option over the others — a human chooses.

Propose 3-4 moves, tailored to what this specific recommendation leaves uncertain. \
Each move must name a concrete action, and its rationale must point at a specific gap \
or weak claim it would resolve. Generic advice is useless here.

Rules:
  - Tailor to the gaps. A run where most claims were killed needs evidence-gathering \
moves; a run with a strong verdict needs moves that test the riskiest assumption.
  - Always include a genuine "pass" / "don't build this" option. It must be a real \
choice, phrased without judgement, even when the verdict is positive.
  - Never propose a move that assumes the idea is worth building.
  - Do not restate the recommendation. Only propose moves.
"""

FALLBACK_MOVES = [
    NextMove(
        move_id="customer_interviews",
        label="Talk to 5 people in the target audience",
        rationale="Direct evidence is the fastest way to close the gaps above.",
    ),
    NextMove(
        move_id="pass",
        label="Pass on this idea",
        rationale="The evidence doesn't justify further investment right now.",
    ),
]


class NextMoveMenu(BaseModel):
    moves: list[NextMove] = Field(description="3-4 tailored options.")


def human_gate_node(state: RunState) -> dict:
    """
    Reads:  recommendation
    Returns: {next_moves, stage}
    """
    run_id = state.get("run_id", "")
    rec: Recommendation | None = state.get("recommendation")

    with timed_event(run_id, "human_gate", Stage.HUMAN_GATE, _summarize(rec)) as ev:
        if rec is None:
            # Reaching the gate with no recommendation means an upstream node failed.
            # Still give the human a real choice rather than dead-ending the run.
            ev["output_summary"] = "no recommendation — offered fallback moves"
            result = {"next_moves": list(FALLBACK_MOVES), "stage": Stage.HUMAN_GATE}
        else:
            menu = generate_structured(
                _prompt(rec),
                NextMoveMenu,
                effort="high",
                system_instruction=SYSTEM,
            )
            moves = menu.moves or list(FALLBACK_MOVES)
            ev["output_summary"] = f"offered {len(moves)} moves"
            result = {"next_moves": moves, "stage": Stage.HUMAN_GATE}

    result["events"] = [ev["event"]]
    return result


def _prompt(rec: Recommendation) -> str:
    findings = "\n".join(
        f"- {g.lane_name}:\n" + "\n".join(f"    - {p}" for p in g.points)
        for g in rec.findings
    )
    gaps = "\n".join(f"- {g}" for g in rec.gaps) or "- (none recorded)"
    return (
        f"Core question: {rec.core_question}\n\n"
        f"Verdict:\n{rec.verdict}\n\n"
        f"Surviving findings:\n{findings or '- (none survived)'}\n\n"
        f"Known gaps — these are what the moves should target:\n{gaps}"
    )


def _summarize(rec: Recommendation | None) -> str:
    return rec.core_question if rec else "(no recommendation)"
