"""
Merge node (merge_node).

Synthesizes the Skeptic's surviving claims into a single one-page Recommendation.
Pure reasoning: no tool calls, no network I/O beyond the single structured LLM call.
See workflows/05_merge_recommendation.md for the full spec.
"""
from __future__ import annotations

from agents.prompts.merge import MERGE_SYSTEM_INSTRUCTION, build_merge_prompt
from graph.llm import generate_structured
from graph.state import Recommendation, RunState, Stage, Verdict
from tools.run_logger import track


def _format_surviving_claims_block(judged, lane_names: dict[str, str]) -> str:
    """
    Renders ONLY surviving claims (SURVIVES / SURVIVES_WITH_CAVEAT), grouped by lane.
    Killed claims are never included here — this is what makes it structurally
    impossible for a killed claim to leak into the model's output.

    `lane_names` maps lane_id -> the human-readable ResearchLane.name (e.g.
    "competitors" -> "Competitors"). Claim only carries lane_id, so without this the
    model's only cue for FindingGroup.lane_name would be the raw slug — falls back to
    the slug if a lane_id has no match (e.g. state["lanes"] wasn't populated).
    """
    survivors = [j for j in judged if j.verdict != Verdict.KILLED]
    if not survivors:
        return "(no claims survived Skeptic review)"

    by_lane: dict[str, list[str]] = {}
    for j in survivors:
        line = j.claim.text
        if j.verdict == Verdict.SURVIVES_WITH_CAVEAT and j.caveat:
            line = f"{line} (caveat: {j.caveat})"
        by_lane.setdefault(j.claim.lane_id, []).append(line)

    lines: list[str] = []
    for lane_id, points in by_lane.items():
        display_name = lane_names.get(lane_id, lane_id)
        lines.append(f"--- Lane: {display_name} ---")
        for point in points:
            lines.append(f"  - {point}")
    return "\n".join(lines)


def merge_node(state: RunState) -> dict:
    """
    Reads state["skeptic_report"], state["brief"], state["lanes"].
    Returns {"recommendation", "stage", "events"} as a partial dict.

    `lanes` is read only to resolve lane_id -> the human-readable ResearchLane.name
    for the prompt (Claim only carries lane_id) — Merge does no other reasoning over
    it, findings/judgements come entirely from skeptic_report.

    Only SURVIVES / SURVIVES_WITH_CAVEAT claims are ever handed to the model — killed
    claims are filtered out before the prompt is built, so they cannot leak into the
    Recommendation.
    """
    run_id = state["run_id"]
    brief = state["brief"]
    if brief is None:
        raise ValueError("merge_node requires state['brief'] to be populated by Intake")

    skeptic_report = state["skeptic_report"]
    if skeptic_report is None:
        raise ValueError("merge_node requires state['skeptic_report'] to be populated by Skeptic")

    lane_names = {lane.lane_id: lane.name for lane in state.get("lanes", [])}
    gaps_block = "\n".join(f"- {g}" for g in skeptic_report.gaps) or "(no gaps flagged)"

    prompt = build_merge_prompt(
        core_question=brief.core_question,
        niche=brief.niche,
        audience=brief.audience,
        surviving_claims_block=_format_surviving_claims_block(
            skeptic_report.judged, lane_names
        ),
        gaps_block=gaps_block,
    )
    survivors_count = sum(1 for j in skeptic_report.judged if j.verdict != Verdict.KILLED)
    input_summary = f"Synthesizing {survivors_count} surviving claim(s) into a recommendation"

    with track(run_id=run_id, agent="Merge", stage=Stage.MERGE, input_summary=input_summary) as holder:
        recommendation = generate_structured(
            prompt,
            Recommendation,
            thinking_level="high",
            system_instruction=MERGE_SYSTEM_INSTRUCTION,
        )
        holder.output_summary = (
            f"produced recommendation with {len(recommendation.findings)} finding group(s), "
            f"{len(recommendation.gaps)} gap(s)"
        )

    # track() only populates holder.event in its finally clause — read it AFTER the
    # with-block exits, never inside it, or this silently returns no events.
    event_obj = getattr(holder, "event", None)

    return {
        "recommendation": recommendation,
        "stage": Stage.HUMAN_GATE,
        "events": [event_obj] if event_obj else [],
    }
