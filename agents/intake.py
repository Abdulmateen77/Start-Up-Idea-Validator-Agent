"""
Intake — turn a vague idea into a researchable brief. OWNERSHIP: Lead only.

Spec: workflows/01_intake_refine.md

This node does the *reasoning* half of Intake: given the conversation so far, either
produce a brief or ask exactly one more question. The *waiting* half is
`intake_wait_node` in graph/build.py — see the comment there for why they're split.

Multi-turn state lives on Gemini's side. We pass `previous_interaction_id` and the
model still has the thread; we do not resend the transcript. `intake_turns` is kept
purely so the UI can render the conversation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from graph.events import timed_event
from graph.llm import converse_structured
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


def intake_node(state: RunState) -> dict:
    """
    Reads:  raw_idea, intake_turns, intake_interaction_id
    Returns: either {brief, stage} when done, or {intake_turns} with a new question.
    """
    run_id = state.get("run_id", "")
    turns: list[IntakeTurn] = list(state.get("intake_turns") or [])
    raw_idea = state.get("raw_idea", "")
    prev_id = state.get("intake_interaction_id")

    with timed_event(run_id, "intake", Stage.INTAKE, raw_idea) as ev:
        # First turn sends the idea; later turns send only the newest human answer,
        # because Gemini still holds the thread behind previous_interaction_id.
        if prev_id and turns and turns[-1].role == "human":
            prompt = turns[-1].content
        else:
            prompt = f"The human's raw idea:\n\n{raw_idea}"

        # A human who won't converge shouldn't loop forever. Force a decision.
        if _questions_asked(turns) >= MAX_QUESTIONS:
            prompt += (
                "\n\nThis conversation has run long. Do not ask another question. "
                "Produce the best brief you can from what you have and mark it ready, "
                "narrowing to the most plausible specific niche and audience."
            )

        reply = converse_structured(
            prompt,
            IntakeReply,
            previous_interaction_id=prev_id,
            system_instruction=SYSTEM,
        )
        answer, interaction_id = reply.value, reply.interaction_id

        if answer.ready and answer.brief:
            ev["output_summary"] = f"brief ready: {answer.brief.niche}"
            result = {
                "brief": answer.brief,
                "stage": Stage.PLAN,
                "intake_interaction_id": interaction_id,
            }
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
                "intake_interaction_id": interaction_id,
            }

    # The event is only finalised once timed_event's block exits.
    result["events"] = [ev["event"]]
    return result


def _questions_asked(turns: list[IntakeTurn]) -> int:
    return sum(1 for t in turns if t.role == "agent")
