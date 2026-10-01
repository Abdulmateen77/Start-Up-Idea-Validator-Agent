"""
Intake is a pure function of (raw_idea, intake_turns): each call renders the whole
transcript into one prompt, so nothing depends on the LLM provider holding
conversation state. These tests pin that down.
"""

from __future__ import annotations

from unittest.mock import patch

from agents.intake import MAX_QUESTIONS, IntakeReply, build_prompt, intake_node
from graph.state import IdeaBrief, IntakeTurn, Stage

BRIEF = IdeaBrief(niche="n", audience="a", core_question="q?")


def _turns(n_questions: int) -> list[IntakeTurn]:
    out: list[IntakeTurn] = []
    for i in range(n_questions):
        out.append(IntakeTurn(role="agent", content=f"question {i + 1}?"))
        out.append(IntakeTurn(role="human", content=f"answer {i + 1}"))
    return out


def test_first_turn_prompt_is_just_the_idea():
    prompt = build_prompt("AI bookkeeping", [])
    assert "AI bookkeeping" in prompt
    assert "Conversation so far" not in prompt


def test_prompt_carries_the_whole_transcript_in_order():
    prompt = build_prompt("idea", _turns(2))

    assert "Conversation so far" in prompt
    positions = [prompt.index(s) for s in
                 ("Intake: question 1?", "Human: answer 1", "Intake: question 2?", "Human: answer 2")]
    assert positions == sorted(positions)


def test_a_long_conversation_forces_a_decision():
    assert "Do not ask another question" in build_prompt("idea", _turns(MAX_QUESTIONS))
    assert "Do not ask another question" not in build_prompt("idea", _turns(1))


@patch("agents.intake.generate_structured")
def test_resending_the_transcript_means_no_provider_state_is_needed(mock_gen):
    mock_gen.return_value = IntakeReply(ready=False, question="next?", brief=None)
    state = {"run_id": "r", "raw_idea": "idea", "intake_turns": _turns(1)}

    result = intake_node(state)

    sent_prompt = mock_gen.call_args[0][0]
    assert "answer 1" in sent_prompt, "the human's reply must reach the model"
    assert set(result) == {"intake_turns", "stage", "events"}, "no provider handle is stored"
    assert result["intake_turns"][-1] == IntakeTurn(role="agent", content="next?")
    assert result["stage"] == Stage.INTAKE
    assert len(result["events"]) == 1


@patch("agents.intake.generate_structured")
def test_ready_reply_returns_the_brief_and_advances(mock_gen):
    mock_gen.return_value = IntakeReply(ready=True, question=None, brief=BRIEF)

    result = intake_node({"run_id": "r", "raw_idea": "idea", "intake_turns": []})

    assert result["brief"] == BRIEF
    assert result["stage"] == Stage.PLAN
    assert set(result) == {"brief", "stage", "events"}


@patch("agents.intake.generate_structured")
def test_a_concern_is_surfaced_as_the_question_not_swallowed(mock_gen):
    mock_gen.return_value = IntakeReply(
        ready=False, question=None, brief=None, concern="This is a feature request."
    )

    result = intake_node({"run_id": "r", "raw_idea": "add dark mode", "intake_turns": []})

    assert result["intake_turns"][-1].content == "This is a feature request."
