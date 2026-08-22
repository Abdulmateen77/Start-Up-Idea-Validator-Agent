"""
Per-archetype research strategies and playbooks.
Defines methodological guidelines, preferred sources, and query hints for research lanes.
"""
from __future__ import annotations

from pydantic import BaseModel

from graph.state import LaneArchetype


class Playbook(BaseModel):
    """Research strategy and sources for a specific lane archetype."""

    archetype: LaneArchetype
    strategy: str
    preferred_sources: list[str]
    query_hints: list[str]


_PLAYBOOKS: dict[LaneArchetype, Playbook] = {
    LaneArchetype.COMPETITORS: Playbook(
        archetype=LaneArchetype.COMPETITORS,
        strategy=(
            "Focus on direct competitors, incumbent alternatives, and vendor pricing pages. "
            "The claim that matters most is actual documented pricing and packaging tiers. "
            "Prefer scraped pricing pages and product documentation over blog posts citing them."
        ),
        preferred_sources=["vendor pricing pages", "G2", "Capterra", "ProductHunt", "official product docs"],
        query_hints=[
            "{niche} pricing",
            "best {niche} software competitors",
            "{niche} alternatives vs",
            "{niche} tool feature comparison",
        ],
    ),
    LaneArchetype.CUSTOMER_PAIN: Playbook(
        archetype=LaneArchetype.CUSTOMER_PAIN,
        strategy=(
            "Focus on user voices, community threads, review sites, and forums. "
            "Surface direct quotes, complaints, and workarounds from target users. "
            "Individual anecdotes are valid to report as specific user pain points, but never state "
            "a single anecdote as an industry-wide trend."
        ),
        preferred_sources=["Reddit", "Hacker News", "GitHub issues", "G2 reviews", "industry forums", "Twitter/X discussions"],
        query_hints=[
            "{audience} struggles with {niche}",
            "why is {niche} so hard",
            "complaints about existing {niche} tools",
            "{audience} pain points workflow",
        ],
    ),
    LaneArchetype.DISTRIBUTION: Playbook(
        archetype=LaneArchetype.DISTRIBUTION,
        strategy=(
            "Focus on acquisition channels, ad platforms, CAC benchmarks, SEO trends, and case studies "
            "for reaching the target audience. Prefer real reported numbers and proven case studies "
            "over generic listicles of marketing channel names."
        ),
        preferred_sources=["marketing case studies", "industry benchmarks", "SEO search volume data", "community growth reports"],
        query_hints=[
            "how to acquire {audience}",
            "{niche} marketing channels CAC",
            "b2b SaaS customer acquisition {niche}",
            "growth case study {niche}",
        ],
    ),
    LaneArchetype.REGULATORY: Playbook(
        archetype=LaneArchetype.REGULATORY,
        strategy=(
            "Focus on primary sources where possible: statutes, regulator websites, and official compliance guidance. "
            "Any secondary legal commentary or blog post must be explicitly labelled as secondary commentary."
        ),
        preferred_sources=["government regulatory bodies", "official legal statutes", "compliance guidelines", "legal expert analyses"],
        query_hints=[
            "{niche} regulations compliance",
            "legal requirements for {niche}",
            "data privacy laws {niche}",
            "regulatory hurdles {niche}",
        ],
    ),
    LaneArchetype.UNIT_ECONOMICS: Playbook(
        archetype=LaneArchetype.UNIT_ECONOMICS,
        strategy=(
            "Focus on pricing models, gross margins, LTV/CAC benchmarks, and cost structures in this domain. "
            "Prefer named-source financial figures and benchmark reports. Flag any modelled or estimated "
            "numbers as unsourced or estimated."
        ),
        preferred_sources=["industry financial benchmarks", "SaaS metrics reports", "public company filings", "pricing studies"],
        query_hints=[
            "{niche} average contract value ACV",
            "SaaS gross margin benchmarks {niche}",
            "pricing model for {niche}",
            "unit economics {niche} startup",
        ],
    ),
    LaneArchetype.TECHNICAL_FEASIBILITY: Playbook(
        archetype=LaneArchetype.TECHNICAL_FEASIBILITY,
        strategy=(
            "Focus on developer documentation, API availability, existing open-source implementations, "
            "and known architectural bottlenecks. Evaluate whether the core mechanism is technically "
            "viable with current APIs and infrastructure."
        ),
        preferred_sources=["developer documentation", "GitHub repositories", "API references", "technical whitepapers"],
        query_hints=[
            "how to build {niche} API",
            "technical stack for {niche}",
            "open source {niche} implementation",
            "API limitations {niche}",
        ],
    ),
    LaneArchetype.OTHER: Playbook(
        archetype=LaneArchetype.OTHER,
        strategy=(
            "General-purpose rigorous research strategy. Investigate the core question thoroughly across "
            "authoritative web sources, expert commentary, and empirical data. Cross-reference claims "
            "and ensure every finding cites its source or is appropriately flagged."
        ),
        preferred_sources=["authoritative web sources", "industry publications", "expert reports", "official websites"],
        query_hints=[
            "{niche} overview analysis",
            "{niche} trends",
            "how {audience} solves {niche}",
            "research on {niche}",
        ],
    ),
}


def get_playbook(archetype: LaneArchetype | str) -> Playbook:
    """
    Retrieve the playbook for a given lane archetype.
    Never raises. Unknown or OTHER returns the generic OTHER playbook.
    """
    if isinstance(archetype, str):
        try:
            archetype_enum = LaneArchetype(archetype)
        except ValueError:
            archetype_enum = LaneArchetype.OTHER
    else:
        archetype_enum = archetype

    return _PLAYBOOKS.get(archetype_enum, _PLAYBOOKS[LaneArchetype.OTHER])
