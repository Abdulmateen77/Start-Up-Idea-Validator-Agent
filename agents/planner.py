"""
Plan node (plan_node).

Turns the refined IdeaBrief from Intake into a set of independent research lanes.
Pure reasoning: no tool calls, no network I/O beyond the single structured LLM call.
See workflows/02_plan_research_lanes.md for the full spec.
"""
from __future__ import annotations

from agents.prompts.planner import PLANNER_SYSTEM_INSTRUCTION, build_planner_prompt
from graph.llm import generate_structured
from graph.state import ResearchPlan, RunState, Stage
from tools.run_logger import track


def plan_node(state: RunState) -> dict:
    """
    Reads state["brief"]. Returns {"lanes", "stage", "events"} as a partial dict.

    Lanes are decided per-idea by the model (see the prompt) — this node does not
    hardcode a lane count or a default set. It only wires the brief into a
    structured call and hands the result straight through.
    """
    run_id = state["run_id"]
    brief = state["brief"]
    if brief is None:
        raise ValueError("plan_node requires state['brief'] to be populated by Intake")

    prompt = build_planner_prompt(
        niche=brief.niche,
        audience=brief.audience,
        core_question=brief.core_question,
    )
    input_summary = f"Planning lanes for: {brief.core_question}"

    with track(run_id=run_id, agent="Planner", stage=Stage.PLAN, input_summary=input_summary) as holder:
        plan = generate_structured(
            prompt,
            ResearchPlan,
            effort="medium",
            system_instruction=PLANNER_SYSTEM_INSTRUCTION,
        )
        holder.output_summary = f"produced {len(plan.lanes)} lanes"

    # track() only populates holder.event in its finally clause — read it AFTER the
    # with-block exits, never inside it, or this silently returns no events.
    event_obj = getattr(holder, "event", None)

    return {
        "lanes": plan.lanes,
        "stage": Stage.RESEARCH,
        "events": [event_obj] if event_obj else [],
    }
