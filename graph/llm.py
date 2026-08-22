"""
Shared Gemini client factory.

OWNERSHIP: Lead only. Every node and tool that needs an LLM imports from here.
Do NOT construct your own ChatGoogleGenerativeAI — one factory means one place to
change models, temperature, retry policy, and cost tracking.

Usage in a node:

    from graph.llm import get_llm
    from graph.state import ResearchPlan

    plan = get_llm().with_structured_output(ResearchPlan).invoke(prompt)

Always use `.with_structured_output(SomePydanticModel)`. Never parse free text.
"""

from __future__ import annotations

import os
from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI

# Reasoning-heavy stages (Skeptic, Merge) default to the stronger model; cheap
# mechanical stages can pass model=FAST_MODEL.
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
FAST_MODEL = os.getenv("GEMINI_FAST_MODEL", "gemini-2.5-flash")


@lru_cache(maxsize=8)
def get_llm(
    model: str | None = None,
    temperature: float = 0.0,
) -> ChatGoogleGenerativeAI:
    """
    Return a configured Gemini client. Cached per (model, temperature).

    temperature defaults to 0.0 — this pipeline is an evidence tool, not a
    brainstorming tool. Raise it only with a comment explaining why.
    """
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and fill it in."
        )

    return ChatGoogleGenerativeAI(
        model=model or DEFAULT_MODEL,
        temperature=temperature,
        google_api_key=api_key,
    )
