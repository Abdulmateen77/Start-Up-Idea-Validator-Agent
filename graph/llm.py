"""
Shared Gemini client. Every node and tool that needs an LLM imports from here.

OWNERSHIP: Lead only. Do NOT construct your own genai.Client — one factory means one
place to change models, thinking level, retries, and cost tracking.

Model: gemini-3.7-flash (GA 2026-08-13) via the google-genai SDK's **Interactions
API** (`client.interactions.create`). Notes that cost real debugging time:

  * `generate_content` is now the LEGACY path. We use Interactions.
  * `temperature`, `top_p`, `top_k`, `candidate_count` are REMOVED in 3.7. Passing
    them is an error, not a no-op. Reasoning effort is now `thinking_level`:
    "low" | "medium" | "high" (default "medium").
  * Multi-turn is server-side via `previous_interaction_id` — you do NOT resend the
    transcript, and prefilled model turns are no longer supported.
  * Structured output goes through `response_format`, and Gemini rejects union types
    other than Optional. Keep response schemas free of `A | B`.

Usage — single-shot (Planner, Skeptic, Merge, Research):

    from graph.llm import generate_structured
    plan = generate_structured(prompt, ResearchPlan)

Usage — multi-turn (Intake only):

    from graph.llm import converse_structured
    turn = converse_structured(prompt, IntakeReply, previous_interaction_id=prev)
    turn.value, turn.interaction_id
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Generic, Literal, TypeVar

from google import genai
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

ThinkingLevel = Literal["low", "medium", "high"]

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")


@dataclass(slots=True)
class Generated(Generic[T]):
    """A parsed response plus the handle needed to continue the conversation."""

    value: T
    interaction_id: str | None


@lru_cache(maxsize=1)
def get_client() -> genai.Client:
    """The one client. Cached — constructing per call wastes connection setup."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not in the environment. Set it in .env — and note "
            ".env is only read if the entrypoint calls load_dotenv() (api/main.py "
            "does). A correct .env that is never loaded looks exactly like a missing "
            "key from here."
        )
    return genai.Client(api_key=api_key)


def _create(
    prompt: str,
    schema: type[T],
    *,
    thinking_level: ThinkingLevel,
    system_instruction: str | None,
    previous_interaction_id: str | None,
    model: str,
):
    # System instructions are folded into the prompt separated by a blank line —
    # 3.7 treats inline instructions this way, and it keeps us off a parameter whose
    # Interactions-API spelling isn't nailed down yet.
    text = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt

    kwargs = {
        "model": model,
        "input": text,
        "generation_config": {"thinking_level": thinking_level},
        "response_format": {
            "type": "text",
            "mime_type": "application/json",
            "schema": schema.model_json_schema(),
        },
    }
    if previous_interaction_id:
        kwargs["previous_interaction_id"] = previous_interaction_id

    return get_client().interactions.create(**kwargs)


def generate_structured(
    prompt: str,
    schema: type[T],
    *,
    thinking_level: ThinkingLevel = "medium",
    system_instruction: str | None = None,
    model: str = DEFAULT_MODEL,
) -> T:
    """
    Single-shot structured call. Returns a validated instance of `schema`.

    Use "high" thinking for adversarial or synthesis work (Skeptic, Merge) and "low"
    for mechanical extraction. Raises ValueError if the model returns nothing.
    """
    interaction = _create(
        prompt,
        schema,
        thinking_level=thinking_level,
        system_instruction=system_instruction,
        previous_interaction_id=None,
        model=model,
    )
    if not interaction.output_text:
        raise ValueError(f"Gemini returned an empty response for {schema.__name__}")
    return schema.model_validate_json(interaction.output_text)


def converse_structured(
    prompt: str,
    schema: type[T],
    *,
    previous_interaction_id: str | None = None,
    thinking_level: ThinkingLevel = "medium",
    system_instruction: str | None = None,
    model: str = DEFAULT_MODEL,
) -> Generated[T]:
    """
    Multi-turn structured call — Intake only.

    Pass the previous turn's `interaction_id` to continue; history lives server-side,
    so do not resend the transcript.
    """
    interaction = _create(
        prompt,
        schema,
        thinking_level=thinking_level,
        system_instruction=system_instruction,
        previous_interaction_id=previous_interaction_id,
        model=model,
    )
    if not interaction.output_text:
        raise ValueError(f"Gemini returned an empty response for {schema.__name__}")
    return Generated(
        value=schema.model_validate_json(interaction.output_text),
        interaction_id=getattr(interaction, "id", None),
    )
