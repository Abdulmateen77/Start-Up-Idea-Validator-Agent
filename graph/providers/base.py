"""
The provider seam. OWNERSHIP: Lead only.

Everything the pipeline needs from an LLM is one operation: given a prompt and a
Pydantic schema, return a validated instance of that schema. That is the whole
contract a provider has to satisfy, which is what keeps the rest of the codebase
provider-neutral — nodes never see a vendor SDK, a vendor parameter name, or a
vendor response shape.

Deliberately NOT part of the contract:
  * multi-turn state — providers differ on whether history lives server-side, so
    callers that need a conversation render the transcript into the prompt
  * sampling knobs (temperature / top_p / top_k) — newer models are dropping them,
    and nothing in this pipeline wants randomness
  * tools / function calling — the Research agent's tools are our own Python
    functions, orchestrated by LangGraph, not by the model vendor
"""

from __future__ import annotations

from typing import Literal, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

# Provider-neutral reasoning dial. Each provider maps this onto its own mechanism
# (a thinking budget, an effort level, a model tier) or ignores it if it has none.
Effort = Literal["low", "medium", "high"]


class LLMError(RuntimeError):
    """Base for failures the pipeline should surface to the user, not swallow."""


class LLMRefusalError(LLMError):
    """The model declined to answer (safety classifier / policy)."""

    def __init__(self, message: str, category: str | None = None):
        super().__init__(message)
        self.category = category


class LLMTruncatedError(LLMError):
    """Output hit the token ceiling, so the structured response is incomplete."""


class LLMEmptyResponseError(LLMError):
    """The call succeeded but returned no usable content."""


class LLMProvider(Protocol):
    """What a provider must implement. One method, on purpose."""

    name: str
    default_model: str

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
        """Return a validated `schema` instance, or raise an LLMError subclass."""
        ...
