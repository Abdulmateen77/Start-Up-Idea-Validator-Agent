"""
Claude via the official `anthropic` SDK. OWNERSHIP: Lead only.

Choices that are easy to get wrong with current Claude models:

  * Structured output uses `output_config.format` (a JSON schema), NOT forced tool
    use — recent models reject `tool_choice: any|tool` with a 400.
  * `thinking` is never sent. On current models thinking is on by default and an
    explicit `{"type": "disabled"}` is rejected; depth is steered by
    `output_config.effort` instead.
  * Sampling params (temperature / top_p / top_k) are never sent — removed on
    current models, and a 400 if present.
  * We call `messages.create` and validate with Pydantic ourselves rather than using
    the SDK's `messages.parse()` helper. `parse()` runs its JSON parse before we can
    look at `stop_reason`, so a refusal or a max_tokens truncation would surface as
    an opaque validation error instead of the real cause.
  * Credentials are resolved by the SDK (ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, or
    an `ant auth login` profile), so we deliberately do NOT pre-check the env var —
    an unset key does not mean there are no credentials.
"""

from __future__ import annotations

from typing import Any

import anthropic
from anthropic import transform_schema
from pydantic import ValidationError

from graph.providers.base import (
    Effort,
    LLMEmptyResponseError,
    LLMError,
    LLMRefusalError,
    LLMTruncatedError,
    T,
)

DEFAULT_MODEL = "claude-opus-5-5"

# Model families that accept `output_config.effort`. Anything else (Haiku 4.5, older
# models) rejects it with a 400, so for those we simply don't send it and the model
# runs at its own default depth. Substring match keeps this working across future
# point releases within a family.
_EFFORT_CAPABLE = (
    "opus-4-5", "opus-4-6", "opus-4-7", "opus-4-8", "opus-5",
    "sonnet-4-6", "sonnet-5", "fable", "mythos",
)


def supports_effort(model: str) -> bool:
    return any(family in model for family in _EFFORT_CAPABLE)


class AnthropicProvider:
    name = "anthropic"
    default_model = DEFAULT_MODEL

    def __init__(self, client: anthropic.Anthropic | None = None):
        self._client = client

    @property
    def client(self) -> anthropic.Anthropic:
        # Lazy: constructing the provider (and importing this module) must never
        # require credentials, so tests and tooling stay hermetic.
        if self._client is None:
            self._client = anthropic.Anthropic()
        return self._client

    def complete_structured(
        self,
        *,
        prompt: str,
        schema: type[T],
        system: str | None,
        effort: Effort,
        model: str | None,
        max_tokens: int,
    ) -> T:
        resolved_model = model or self.default_model

        output_config: dict[str, Any] = {
            "format": {
                "type": "json_schema",
                # transform_schema strips constraints the API can't enforce (min/max
                # lengths, numeric bounds); Pydantic re-enforces them below.
                "schema": transform_schema(schema.model_json_schema()),
            }
        }
        if supports_effort(resolved_model):
            output_config["effort"] = effort

        request: dict[str, Any] = {
            "model": resolved_model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
            "output_config": output_config,
        }
        if system:
            request["system"] = system

        response = self.client.messages.create(**request)

        # Check WHY it stopped before trusting the content: a refusal or a truncated
        # response will not be valid JSON and would otherwise masquerade as a
        # schema-validation failure.
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            category = getattr(details, "category", None)
            raise LLMRefusalError(
                f"{resolved_model} declined to answer for {schema.__name__}"
                + (f" (category: {category})" if category else ""),
                category=category,
            )
        if response.stop_reason == "max_tokens":
            raise LLMTruncatedError(
                f"{resolved_model} hit max_tokens={max_tokens} while producing "
                f"{schema.__name__}; the structured output is incomplete. Raise "
                "LLM_MAX_TOKENS or shrink the input."
            )

        text = next((b.text for b in response.content if b.type == "text"), "")
        if not text.strip():
            raise LLMEmptyResponseError(
                f"{resolved_model} returned no text for {schema.__name__}"
            )

        try:
            return schema.model_validate_json(text)
        except ValidationError as exc:
            raise LLMError(
                f"{resolved_model} returned JSON that does not match "
                f"{schema.__name__}: {exc}"
            ) from exc
