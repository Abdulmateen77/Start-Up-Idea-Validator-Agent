# Brief — HERMES · BACKEND SESSION

> **You are the backend Hermes session.** A second Hermes session
> (`briefs/HERMES_FRONTEND.md`) is building the Next.js app **at the same time**.
> You share an agent name; you do **not** share files.
>
> **You never touch `frontend/`.** Not one file. That session never touches Python.

**Your half of the project: evidence.** The deterministic tool layer, plus the one
node that uses it. Everything you build is testable without a live API.

**Read first:** `briefs/RULES.md` → `CLAUDE.md` → `docs/ARCHITECTURE.md` →
`graph/state.py` → `workflows/03_research_lane.md` → `workflows/07_supervisor_monitoring.md`

---

## Files you own — create these, nothing else

```
tools/__init__.py
tools/errors.py            # typed exceptions
tools/firecrawl_client.py  # search + scrape, the only place Firecrawl is called
tools/playbooks.py         # per-archetype research strategies
tools/run_logger.py        # AgentEvent → logs/ (Supervisor's audit trail)
agents/research.py         # research_node() — the fanned-out lane worker
tests/test_tools_firecrawl.py
tests/test_tools_playbooks.py
tests/test_tools_logger.py
tests/test_agents_research.py
```

**Do not touch:** `graph/`, `api/`, or any `agents/*.py` other than `research.py`.

---

## Task 1 — `tools/errors.py`

Typed exceptions so failures are catchable, not string-matched.

```python
class ToolError(Exception):          # base
class SearchError(ToolError):
class ScrapeError(ToolError):
class RateLimitError(ToolError):     # carries retry_after: float | None
```

## Task 2 — `tools/firecrawl_client.py`

The **only** module in the repo that talks to Firecrawl. Two public functions:

```python
def search(query: str, limit: int = 5) -> list[SearchHit]
def scrape(url: str) -> ScrapedPage
```

Define `SearchHit` and `ScrapedPage` as Pydantic models **local to this module** —
they're tool-layer types, not pipeline contracts, so they don't belong in
`graph/state.py`.

Requirements:
- Read `FIRECRAWL_API_KEY` via `os.getenv`. Raise a clear error if missing.
- Retry with exponential backoff on rate-limit / 5xx. Cap retries (3 is fine).
- Raise `RateLimitError` / `SearchError` / `ScrapeError` on give-up. **Never return
  an empty list to signal an error** — an empty result and a dead scraper must be
  distinguishable by the caller.
- Return clean markdown/text from `scrape`, not raw HTML.
- Document real Firecrawl behaviour you discover (rate limits, timeouts, quirks) in
  your report — the Lead will fold it into `workflows/03_research_lane.md`.

## Task 3 — `tools/playbooks.py`

**There is exactly ONE Research agent.** Customer Pain / Competitors / Distribution
are *not* separate agents — they are the same node run in parallel with different
questions. What legitimately differs between them is **method**, and that lives here.

```python
class Playbook(BaseModel):        # local to this module, not a pipeline contract
    archetype: LaneArchetype
    strategy: str                 # prompt fragment injected into the research prompt
    preferred_sources: list[str]  # e.g. ["vendor pricing pages", "G2", "Capterra"]
    query_hints: list[str]        # search-query shapes that work for this lane type

def get_playbook(archetype: LaneArchetype) -> Playbook:
    """Never raises. Unknown/OTHER → the generic playbook."""
```

Import `LaneArchetype` from `graph.state`. Write a playbook for each value:

- `COMPETITORS` — find vendor pricing pages and scrape them; comparison sites; **the
  claim that matters is the actual price**, so prefer a scraped pricing page over a
  blog post citing one.
- `CUSTOMER_PAIN` — forums, subreddits, review sites, community threads. Sources are
  *user voices*. Individual anecdotes are fine to report — but never state one as a
  trend; Skeptic will kill it and it deserves to be killed.
- `DISTRIBUTION` — channels, ad platforms, CAC benchmarks, case studies. Prefer real
  reported numbers over listicles of channel names.
- `REGULATORY` — primary sources only where possible: statutes, regulator sites,
  official guidance. Secondary commentary must be labelled as such.
- `UNIT_ECONOMICS` — pricing, margins, benchmarks. Prefer named-source figures;
  flag any modelled/estimated number as unsourced.
- `TECHNICAL_FEASIBILITY` — docs, API references, existing implementations.
- `OTHER` — **the generic fallback, and it must genuinely work on its own.** The
  Planner invents lanes per-idea; a lane with no matching archetype is normal and
  must produce good research anyway. Do not treat OTHER as a degraded path.

`get_playbook` must be **pure and total** — no network, no LLM, never raises.

## Task 4 — `tools/run_logger.py`

The Supervisor's persistence. Every node will use this.

```python
def log_event(event: AgentEvent) -> None      # append-only JSONL to logs/<run_id>.jsonl
def read_run(run_id: str) -> list[AgentEvent]
def summarize_run(run_id: str) -> str         # human-readable run summary
```

- Import `AgentEvent` from `graph.state`. Do not redefine it.
- Append-only. Never rewrite or truncate an existing log.
- Create `logs/` if absent. `logs/` is gitignored — that's intentional.
- Also provide a small helper nodes can use so they don't hand-roll timing:

```python
@contextmanager
def track(run_id: str, agent: str, stage: Stage, input_summary: str):
    """Times the block, builds the AgentEvent, logs it, yields a slot for
    output_summary. On exception: logs ok=False with the error, then re-raises."""
```

Get this helper right — Antigravity and the Lead both build on it.

## Task 5 — `agents/research.py`

The lane worker. Fanned out via LangGraph's `Send`, so it receives **`LaneTask`, not
`RunState`** (see `docs/ARCHITECTURE.md` → Node signatures).

```python
def research_node(task: LaneTask) -> dict:
    # returns {"findings": [LaneFindings(...)], "events": [AgentEvent(...)]}
```

Follow `workflows/03_research_lane.md` exactly. Specifically:

0. Load the lane's playbook: `get_playbook(task["lane"].archetype)`. Inject its
   `strategy` into your prompt and let `query_hints` / `preferred_sources` shape the
   searches. **One node, one code path** — the playbook is data, not a branch. If you
   find yourself writing `if archetype == COMPETITORS:` in this file, the logic
   belongs in `tools/playbooks.py` instead.
1. Break the lane question into 1–3 searchable sub-questions.
2. Gather evidence with `tools/firecrawl_client.py`.
3. **Every claim records a source.** No source found → `unsourced=True` and a `Source`
   with a `note`. Skeptic depends on that flag being honest.
4. Nothing found at all → `no_evidence_found=True`. This is a valid finding.
5. Tool failures → append to `LaneFindings.tool_failures`. Retry if reasonable.
   Never swallow.
6. **Do not editorialize on whether the idea is good.** Report what was found. Verdicts
   are Merge's job, after Skeptic filters.

Use `get_llm().with_structured_output(...)` from `graph.llm` for turning scraped text
into `Claim` objects. Never parse free text.

## Task 6 — tests

- `test_tools_firecrawl.py` — mock the HTTP layer. Cover: happy path, rate limit +
  retry, give-up raises the right typed error, scrape returns clean text.
- `test_tools_playbooks.py` — **every** `LaneArchetype` value returns a playbook;
  `OTHER` returns a usable generic one; `get_playbook` never raises and never
  touches the network.
- `test_tools_logger.py` — round-trip an event, assert append-only across two writes,
  assert `track` logs `ok=False` and re-raises on exception.
- `test_agents_research.py` — mock `get_llm` **and** the Firecrawl client. Assert:
  returns `{"findings": [...], "events": [...]}` with `findings` a **single-item
  list**; `no_evidence_found=True` when search returns nothing; `tool_failures`
  populated when the client raises; **a lane with `archetype=OTHER` researches
  successfully** (the generic path is not a degraded path).

**No test may hit a live API or a real LLM.**

---

## Definition of done

- All 10 files exist, all tests pass offline.
- `research_node` returns exactly the contract shape in `docs/ARCHITECTURE.md`.
- Nothing outside your file list was created or modified.
- Report back in the 5-section format from `briefs/RULES.md` §9.

## Ask the Lead before you

- Add or change anything in `graph/state.py` (you may not — report instead).
- Run a live Firecrawl or Gemini call (**costs money**).
- Add a dependency beyond: `firecrawl-py`, `pydantic`, `langchain-google-genai`, `pytest`.
