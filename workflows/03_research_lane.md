# Workflow: Research — Investigate One Lane

## Objective
Gather evidence for a single research lane's question and report back with sources.
This workflow is generic — the same steps apply whether the lane is Customer Pain,
Competitors, Distribution, or something else the Planner defined.

One Research agent instance runs per lane, all in parallel, all independent.

## Required Inputs
- Lane name + specific question from Plan.
- Idea brief (niche, audience) for context.

## Steps
1. Read the lane's question. Break it into 1-3 searchable sub-questions if needed.
2. Gather evidence using available tools (web search, scraping, forum/review mining,
   pricing page lookups, etc. — see Tools below).
3. For every claim, record the source (URL, doc, or explicit "no source found").
   Claims without a source are still reported, but flagged as unsourced — the
   Skeptic stage relies on this flag.
4. Summarize findings for the lane in a short structured format (see Output).
5. Do not editorialize about whether the idea is good — that's Merge's job, after
   Skeptic has filtered the evidence. This stage reports what was found, plainly.

## Tools
Not built yet. Expected tools once implementation starts:
- A web search tool (query → results)
- A page fetch/scrape tool (URL → clean text)
- Possibly a structured-extraction tool (raw text → claim + source pairs)

## Expected Output
```
Lane: Competitors
Findings:
  - Claim: "X charges $49/mo for bookkeeping automation targeting Shopify sellers"
    Source: https://example.com/pricing
  - Claim: "Several merchants report switching away from X due to poor reconciliation"
    Source: unsourced (seen referenced in a forum thread, not independently verified)
```

## Edge Cases
- **No evidence found for the question**: report that explicitly — "no evidence
  found" is a valid, useful finding, not a failure to hide.
- **Conflicting evidence within the same lane**: report both sides with sources;
  don't pick a winner — that's what Skeptic and Merge are for.
- **Tool failure (rate limit, blocked scrape, etc.)**: report the failure to the
  Supervisor, retry with backoff if reasonable, don't silently return an empty result
  as if nothing was wrong.
