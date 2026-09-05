"""
Prompt text for the Plan stage. Kept separate from agents/planner.py so the prompt
can be iterated on without touching node wiring.
"""
from __future__ import annotations

PLANNER_SYSTEM_INSTRUCTION = (
    "You are the Planner in an idea-validation pipeline. You turn a refined idea "
    "brief into a small set of independent research lanes that will run in parallel."
)

PLANNER_PROMPT_TEMPLATE = """\
Decompose the idea brief below into research lanes for a single question:
"{core_question}"

IDEA BRIEF
- Niche: {niche}
- Audience: {audience}
- Core question: {core_question}

RULES

1. Lanes are decided per-idea, never fixed. "Customer Pain", "Competitors", and
   "Distribution" are examples from ONE reference idea, not a template you must
   reuse. This idea may need different lanes entirely (e.g. Regulatory, Unit
   Economics, Technical Feasibility) — or fewer or more of them. Do not force-fit
   a default set and do not pad the list to hit a particular count. Two lanes is
   fine. Five lanes is fine.

2. Each lane needs one specific, answerable question. It must NOT be a
   restatement of the core question above — it should be a concrete sub-question
   that, once answered, gives evidence bearing on the core question.

3. Lanes must be genuinely independent, because they run in parallel and cannot
   see each other's results. If a lane's question can only be answered after
   another lane's question is answered, they are not independent — merge them
   into a single lane instead of creating two that secretly depend on each other.

4. Tag every lane with the archetype that matches its RESEARCH METHOD, not its
   topic keyword. For example, a lane about what rivals charge is COMPETITORS
   (you'd study competitor pricing pages), not UNIT_ECONOMICS, even though
   "pricing" sounds like an economics topic. Available archetypes: CUSTOMER_PAIN,
   COMPETITORS, DISTRIBUTION, REGULATORY, UNIT_ECONOMICS, TECHNICAL_FEASIBILITY,
   OTHER. OTHER is a first-class, valid answer when nothing else fits — never
   distort a lane's question just to force it into one of the named archetypes.

5. Give each lane a short, stable lane_id slug (e.g. "competitors",
   "customer_pain") and a human-readable name (e.g. "Competitors").

Return the research plan as structured output matching the given schema.
"""


def build_planner_prompt(niche: str, audience: str, core_question: str) -> str:
    """Fill the template with the brief's fields."""
    return PLANNER_PROMPT_TEMPLATE.format(
        niche=niche, audience=audience, core_question=core_question
    )
