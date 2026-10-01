"""
Intake — turn a vague idea into a researchable brief. OWNERSHIP: Lead only.

Spec: workflows/01_intake_refine.md

This node does the *reasoning* half of Intake: given the conversation so far, either
produce a brief or ask exactly one more question. The *waiting* half is
`intake_wait_node` in graph/build.py — see the comment there for why they're split.

Intake is a pure function of (raw_idea, intake_turns). Each call renders the whole
transcript into one prompt, so nothing depends on the LLM provider remembering the
conversation. That is deliberate: providers differ on whether history lives
server-side, and a design that assumes it does cannot be moved to another provider.
The transcript is short (capped at MAX_QUESTIONS), so resending it is cheap.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from graph.events import timed_event
from graph.llm import generate_structured
from graph.state import IdeaBrief, IntakeTurn, RunState, Stage

SYSTEM = """\
You are the Intake stage of an idea-validation pipeline. Your only job is to turn a \
vague idea into something concrete enough to research. You are not evaluating whether \
the idea is good — later stages do that.

An idea is ready ONLY when all three are true:
  - niche is specific (NOT "the market", NOT "small businesses")
  - audience is a specific role plus company size or stage
  - there is a single core question the pipeline can investigate

Rules:
  - Ask ONE question at a time. Never send a questionnaire.
  - Ask only what actually blocks research. Do not gather nice-to-know detail.
  - If the idea already contains all three, set ready immediately and do not ask \
anything — confirming a brief back to the human is not a reason to burn a turn.
  - If the human has stayed vague across two or more answers, STOP asking open \
questions. Offer 2-3 concrete candidate niches/audiences and let them pick. Never \
invent a niche for them.
  - Never repeat a question that already appears in the conversation so far.
  - If this is not really a build/no-build decision (it's a feature request, or a \
research question with no product behind it), set concern and explain why. The rest \
of the pipeline assumes a build decision at the end.
"""

MAX_QUESTIONS = 6


class IntakeReply(BaseModel):
    """Intake's structured turn. Exactly one of question/brief is meaningful."""

    ready: bool = Field(description="True when the brief below is complete.")
    question: str | None = Field(
        default=None, description="The single next question. Null when ready."
    )
    brief: IdeaBrief | None = Field(
        default=None, description="Populated only when ready is true."
    )
    concern: str | None = Field(
        default=None,
        description="Set when this isn't a build/no-build decision. Otherwise null.",
    )


def build_prompt(raw_idea: str, turns: list[IntakeTurn]) -> str:
    """Render the full conversation so far into one self-contained prompt."""
    parts = [f"The human's raw idea:\n\n{raw_idea}"]

    if turns:
        transcript = "\n".join(
            f"{'Intake' if t.role == 'agent' else 'Human'}: {t.content}" for t in turns
        )
        parts.append(f"Conversation so far:\n\n{transcript}")

    # A human who won't converge shouldn't loop forever. Force a decision.
    if _questions_asked(turns) >= MAX_QUESTIONS:
        parts.append(
            "This conversation has run long. Do not ask another question. Produce "
            "the best brief you can from what you have and mark it ready, narrowing "
            "to the most plausible specific niche and audience."
        )
    else:
        parts.append("Either mark the brief ready, or ask the single next question.")

    return "\n\n".join(parts)


def intake_node(state: RunState) -> dict:
    """
    Reads:  raw_idea, intake_turns
    Returns: either {brief, stage} when done, or {intake_turns} with a new question.
    """
    run_id = state.get("run_id", "")
    turns: list[IntakeTurn] = list(state.get("intake_turns") or [])
    raw_idea = state.get("raw_idea", "")

    with timed_event(run_id, "intake", Stage.INTAKE, raw_idea) as ev:
        answer = generate_structured(
            build_prompt(raw_idea, turns),
            IntakeReply,
            effort="medium",
            system_instruction=SYSTEM,
        )

        if answer.ready and answer.brief:
            ev["output_summary"] = f"brief ready: {answer.brief.niche}"
            result = {"brief": answer.brief, "stage": Stage.PLAN}
        else:
            # A concern still needs a human reply, so it rides out as the question
            # rather than silently stalling the run.
            question = answer.concern or answer.question or (
                "Who exactly is this for, and what problem does it solve for them?"
            )
            ev["output_summary"] = f"asked: {question}"
            result = {
                "intake_turns": [*turns, IntakeTurn(role="agent", content=question)],
                "stage": Stage.INTAKE,
            }

    # The event is only finalised once timed_event's block exits.
    result["events"] = [ev["event"]]
    return result


def _questions_asked(turns: list[IntakeTurn]) -> int:
    return sum(1 for t in turns if t.role == "agent")
