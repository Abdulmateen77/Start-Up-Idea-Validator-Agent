"""
Research lane worker node (research_node).
Fanned out via LangGraph's Send API, receiving a LaneTask.
Executes searches and scrapes using playbook strategies and logs execution via Supervisor.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from graph.llm import generate_structured
from graph.state import (
    Claim,
    LaneFindings,
    LaneTask,
    Source,
    Stage,
    ToolFailure,
)
from tools.errors import ToolError
from tools.firecrawl_client import scrape, search
from tools.playbooks import get_playbook
from tools.run_logger import track


class ExtractedClaim(BaseModel):
    claim_id: str
    text: str
    source_url: str | None = Field(default=None, description="URL if found")
    source_title: str | None = Field(default=None, description="Title if found")
    source_note: str | None = Field(default=None, description="Note if unverified/referenced")
    unsourced: bool = Field(default=False)


class ExtractionResult(BaseModel):
    claims: list[ExtractedClaim] = Field(default_factory=list)


def research_node(task: LaneTask) -> dict:
    """
    Research worker node. Receives a LaneTask, executes searches and scrapes
    guided by the lane's playbook, extracts claims using structured LLM calls,
    and returns findings and supervisor events.
    """
    run_id = task["run_id"]
    lane = task["lane"]
    brief = task["brief"]

    playbook = get_playbook(lane.archetype)

    input_summary = f"Researching lane '{lane.name}': {lane.question}"
    tool_failures: list[ToolFailure] = []
    claims: list[Claim] = []
    no_evidence_found = False

    with track(run_id=run_id, agent="Research", stage=Stage.RESEARCH, input_summary=input_summary) as holder:
        # Step 1: Formulate search queries using lane question, brief, and playbook query hints
        queries: list[str] = []
        for hint in playbook.query_hints:
            try:
                formatted = hint.format(
                    niche=brief.niche,
                    audience=brief.audience,
                    core_question=brief.core_question,
                )
                queries.append(formatted)
            except Exception:
                pass
        # Add the main lane question as a query
        queries.append(lane.question)

        # Deduplicate while preserving order
        seen_queries: set[str] = set()
        unique_queries: list[str] = []
        for q in queries:
            q_clean = q.strip()
            if q_clean and q_clean not in seen_queries:
                seen_queries.add(q_clean)
                unique_queries.append(q_clean)

        # Take top 3 queries
        search_queries = unique_queries[:3]

        all_search_hits = []
        for q in search_queries:
            try:
                hits = search(q, limit=3)
                all_search_hits.extend(hits)
            except ToolError as e:
                tool_failures.append(
                    ToolFailure(
                        tool="firecrawl_search",
                        error=str(e),
                        retried=True,
                        recovered=False,
                    )
                )
            except Exception as e:
                tool_failures.append(
                    ToolFailure(
                        tool="firecrawl_search",
                        error=str(e),
                        retried=False,
                        recovered=False,
                    )
                )

        if not all_search_hits and not search_queries:
            no_evidence_found = True
        else:
            # Deduplicate hits by URL
            seen_urls: set[str] = set()
            unique_hits = []
            for hit in all_search_hits:
                if hit.url and hit.url not in seen_urls:
                    seen_urls.add(hit.url)
                    unique_hits.append(hit)

            if not unique_hits:
                no_evidence_found = True
            else:
                # Scrape top 3 unique URLs to gather raw content
                scraped_texts = []
                for hit in unique_hits[:3]:
                    try:
                        page = scrape(hit.url)
                        scraped_texts.append(
                            f"Source URL: {page.url}\nTitle: {page.title or hit.title or 'Unknown'}\nContent:\n{page.markdown[:4000]}"
                        )
                    except ToolError as e:
                        tool_failures.append(
                            ToolFailure(
                                tool="firecrawl_scrape",
                                error=f"{hit.url}: {e}",
                                retried=True,
                                recovered=False,
                            )
                        )
                    except Exception as e:
                        tool_failures.append(
                            ToolFailure(
                                tool="firecrawl_scrape",
                                error=f"{hit.url}: {e}",
                                retried=False,
                                recovered=False,
                            )
                        )

                if not scraped_texts:
                    snippet_texts = [
                        f"Source URL: {h.url}\nTitle: {h.title}\nSnippet: {h.description or h.markdown or ''}"
                        for h in unique_hits[:5]
                    ]
                    combined_text = "\n\n---\n\n".join(snippet_texts)
                else:
                    combined_text = "\n\n---\n\n".join(scraped_texts)

                if not combined_text.strip():
                    no_evidence_found = True
                else:
                    # Step 2: Extract claims using structured LLM call (effort="low")
                    prompt = f"""
You are a rigorous research analyst. Extract key empirical claims, facts, and data points answering the research question based on the source text provided below.

RESEARCH LANE: {lane.name}
QUESTION: {lane.question}
ARCHETYPE STRATEGY: {playbook.strategy}
PREFERRED SOURCES: {', '.join(playbook.preferred_sources)}

SOURCE TEXT:
{combined_text}

Instructions:
1. Extract 1-5 concrete claims that directly address the question.
2. For each claim, provide a unique claim_id (e.g. "{lane.lane_id}-1"), the claim text, and the source URL/title if available.
3. If a claim is from a secondary mention or unverified source without a clear URL, set unsourced=True and provide a note.
4. Do not editorialize or evaluate whether the idea is good. Report facts only.
"""

                    try:
                        extraction = generate_structured(
                            prompt,
                            ExtractionResult,
                            effort="low",
                            system_instruction="Extract accurate claims with correct source attribution.",
                        )
                        for idx, ec in enumerate(extraction.claims, start=1):
                            sources = []
                            if ec.source_url or ec.source_title:
                                sources.append(
                                    Source(
                                        url=ec.source_url,
                                        title=ec.source_title,
                                        note=ec.source_note,
                                    )
                                )
                            else:
                                sources.append(
                                    Source(
                                        url=None,
                                        title=None,
                                        note=ec.source_note or "Extracted from research search results",
                                    )
                                )

                            claims.append(
                                Claim(
                                    claim_id=ec.claim_id or f"{lane.lane_id}-{idx}",
                                    lane_id=lane.lane_id,
                                    text=ec.text,
                                    sources=sources,
                                    unsourced=ec.unsourced or (not any(s.url for s in sources)),
                                )
                            )
                    except Exception as e:
                        tool_failures.append(
                            ToolFailure(
                                tool="llm_extraction",
                                error=str(e),
                                retried=False,
                                recovered=False,
                            )
                        )

                if not claims and not tool_failures:
                    no_evidence_found = True

        holder.output_summary = (
            f"Extracted {len(claims)} claims for lane '{lane.name}' "
            f"(no_evidence_found={no_evidence_found}, tool_failures={len(tool_failures)})"
        )

    # track() populates holder.event in its finally block, so this has to be read
    # AFTER the with-block exits. Reading it inside always yields None and the node
    # silently returns no events, leaving the Supervisor blind to the whole stage.
    event_obj = getattr(holder, "event", None)

    findings = LaneFindings(
        lane_id=lane.lane_id,
        lane_name=lane.name,
        claims=claims,
        no_evidence_found=no_evidence_found,
        tool_failures=tool_failures,
    )

    events = [event_obj] if event_obj else []
    return {"findings": [findings], "events": events}
