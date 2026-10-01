"""
The one LLM entrypoint. OWNERSHIP: Lead only.

Every node imports `generate_structured` from here and nothing else. Which vendor
answers is a configuration decision, not a code decision:

    LLM_PROVIDER   which provider to use                    (default: anthropic)
    LLM_MODEL      model id; omitted = provider's default   (anthropic: claude-opus-5-5)
    LLM_MAX_TOKENS output ceiling per call                  (default: 16000)

Usage in a node:

    from graph.llm import generate_structured

    plan = generate_structured(prompt, ResearchPlan, effort="medium")

Rules for callers:
  * Always pass a Pydantic schema. Never parse free text.
  * `effort` is the provider-neutral reasoning dial: "low" for mechanical
    extraction, "medium" by default, "high" for adversarial or synthesis work.
  * Keep response schemas simple — no unions beyond Optional, no recursion, no
    reliance on numeric/length constraints for correctness. That is the lowest
    common denominator that every structured-output implementation handles.
  * Multi-turn is the CALLER's job: render the transcript into the prompt. Providers
    differ on whether history lives server-side, so nothing here assumes it does.

Adding a provider = one new file in graph/providers/ implementing `LLMProvider`
(see base.py), plus one `register_provider(...)` call. No node changes.
"""

from __future__ import annotations

import os
from typing import Callable

from graph.providers.base import (
    Effort,
    LLMEmptyResponseError,
    LLMError,
    LLMProvider,
    LLMRefusalError,
    LLMTruncatedError,
    T,
)

__all__ = [
    "Effort",
    "LLMEmptyResponseError",
    "LLMError",
    "LLMProvider",
    "LLMRefusalError",
    "LLMTruncatedError",
    "available_providers",
    "generate_structured",
    "get_provider",
    "register_provider",
    "reset_provider_cache",
]

DEFAULT_PROVIDER = "anthropic"
DEFAULT_MAX_TOKENS = 16000


def _anthropic() -> LLMProvider:
    # Imported lazily so that selecting a different provider never requires the
    # anthropic SDK to be installed (and vice versa for future providers).
    from graph.providers.anthropic_provider import AnthropicProvider

    return AnthropicProvider()


_FACTORIES: dict[str, Callable[[], LLMProvider]] = {"anthropic": _anthropic}
_INSTANCES: dict[str, LLMProvider] = {}


def register_provider(name: str, factory: Callable[[], LLMProvider]) -> None:
    """Make a provider selectable via LLM_PROVIDER. Replaces any existing entry."""
    _FACTORIES[name] = factory
    _INSTANCES.pop(name, None)


def available_providers() -> list[str]:
    return sorted(_FACTORIES)


def reset_provider_cache() -> None:
    """Drop cached provider instances (tests, or after changing env at runtime)."""
    _INSTANCES.clear()


def get_provider() -> LLMProvider:
    """The configured provider, constructed once and reused."""
    name = os.getenv("LLM_PROVIDER", DEFAULT_PROVIDER).strip().lower()
    if name not in _FACTORIES:
        raise ValueError(
            f"Unknown LLM_PROVIDER {name!r}. Available: {', '.join(available_providers())}."
        )
    if name not in _INSTANCES:
        _INSTANCES[name] = _FACTORIES[name]()
    return _INSTANCES[name]


def generate_structured(
    prompt: str,
    schema: type[T],
    *,
    effort: Effort = "medium",
    system_instruction: str | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
) -> T:
    """
    Single structured call. Returns a validated instance of `schema`, or raises an
    `LLMError` subclass (`LLMRefusalError`, `LLMTruncatedError`,
    `LLMEmptyResponseError`) — never an empty or half-parsed result.
    """
    return get_provider().complete_structured(
        prompt=prompt,
        schema=schema,
        system=system_instruction,
        effort=effort,
        model=model or os.getenv("LLM_MODEL") or None,
        max_tokens=max_tokens or int(os.getenv("LLM_MAX_TOKENS", DEFAULT_MAX_TOKENS)),
    )
