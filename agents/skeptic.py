"""
Skeptic node (skeptic_node).

Adversarially reviews every claim from every research lane at once. Pure reasoning:
no tool calls, no network I/O beyond the single structured LLM call.
See workflows/04_skeptic_review.md for the full spec.
"""
from __future__ import annotations

from agents.prompts.skeptic import SKEPTIC_SYSTEM_INSTRUCTION, build_skeptic_prompt
from graph.llm import generate_structured
from graph.state import RunState, SkepticReport, Stage
from tools.run_logger import track


def _format_findings_block(findings) -> str:
    """Renders every lane's claims into one block so the model judges them together —
    cross-lane contradiction detection is impossible if claims are processed in
    isolation, one at a time."""
    lines: list[str] = []
    for lane_findings in findings:
        lines.append(f"--- Lane: {lane_findings.lane_name} (lane_id={lane_findings.lane_id}) ---")
        if lane_findings.no_evidence_found:
            lines.append("  (no evidence found for this lane)")
        if not lane_findings.claims:
            lines.append("  (no claims)")
        for claim in lane_findings.claims:
            sources_desc = "; ".join(
                s.url or s.note or s.title or "unspecified" for s in claim.sources
            ) or "none"
            lines.append(
                f"  claim_id={claim.claim_id} unsourced={claim.unsourced} "
                f"sources=[{sources_desc}]\n    text: {claim.text}"
            )
        if lane_findings.tool_failures:
            lines.append(f"  ({len(lane_findings.tool_failures)} tool failure(s) in this lane)")
    return "\n".join(lines) if lines else "(no findings at all)"


def _format_lane_questions_block(lanes) -> str:
    return "\n".join(f"- [{lane.lane_id}] {lane.name}: {lane.question}" for lane in lanes) or "(no lanes)"


def skeptic_node(state: RunState) -> dict:
    """
    Reads state["findings"], state["brief"], state["lanes"].
    Returns {"skeptic_report", "stage", "events"} as a partial dict.

    Every claim across every lane is judged in a single call so the model can detect
    contradictions between lanes — judging claim-by-claim in isolation would make
    that structurally impossible.
    """
    run_id = state["run_id"]
    brief = state["brief"]
    if brief is None:
        raise ValueError("skeptic_node requires state['brief'] to be populated by Intake")

    findings = state.get("findings", [])
    lanes = state.get("lanes", [])

    prompt = build_skeptic_prompt(
        core_question=brief.core_question,
        niche=brief.niche,
        audience=brief.audience,
        findings_block=_format_findings_block(findings),
        lane_questions_block=_format_lane_questions_block(lanes),
    )
    total_claims = sum(len(f.claims) for f in findings)
    input_summary = f"Judging {total_claims} claims across {len(findings)} lane(s)"

    with track(run_id=run_id, agent="Skeptic", stage=Stage.SKEPTIC, input_summary=input_summary) as holder:
        report = generate_structured(
            prompt,
            SkepticReport,
            effort="high",
            system_instruction=SKEPTIC_SYSTEM_INSTRUCTION,
        )
        survived = sum(1 for j in report.judged if j.verdict.value != "killed")
        holder.output_summary = (
            f"judged {len(report.judged)} claims ({survived} survived), "
            f"{len(report.gaps)} gap(s)"
        )

    # track() only populates holder.event in its finally clause — read it AFTER the
    # with-block exits, never inside it, or this silently returns no events.
    event_obj = getattr(holder, "event", None)

    return {
        "skeptic_report": report,
        "stage": Stage.MERGE,
        "events": [event_obj] if event_obj else [],
    }
