# Idea Validator Agent

## What This Project Is

A multi-agent system that takes a raw, vague idea and runs it through a structured
validation pipeline — turning "should we build X?" into a one-page, evidence-backed
recommendation with a human decision point at the end.

Modeled as one question, run as a graph:

1. **INTAKE** — back-and-forth with the human to turn a vague idea into a detailed,
   comprehensive brief by pinning down a specific niche and target audience. Research
   does not start until the idea is concrete enough to research.
2. **PLAN** — turn the refined brief into research lanes (e.g. Customer Pain,
   Competitors, Distribution). Lanes are decided per-idea by the Planner, not fixed.
3. **RESEARCH (parallel)** — one sub-agent per lane, each gathering evidence
   independently and reporting back with sources.
4. **SKEPTIC** — attacks every claim coming out of research. Weak or unsupported
   claims don't survive. Checking the evidence is its own job, not an afterthought.
5. **MERGE** — surviving claims get synthesized into a single one-page recommendation.
6. **HUMAN GATE** — the recommendation is presented with a short menu of next moves
   (e.g. customer interviews, competitor teardown, build a calculator, pass). The
   human decides the next move — not the model.

Running alongside the linear flow (not a step in it): a **SUPERVISOR** agent that
logs and monitors every other agent — inputs, outputs, timing, failures, cost — for
observability and debugging.

## Agent Roles

| Agent | Role | Input | Output |
|---|---|---|---|
| Intake | Interactive refinement — pins down a specific niche + audience from a vague idea | Raw idea (human, often one vague sentence) | Detailed idea brief: niche, audience, core question |
| Planner | Decomposes the brief into research lanes | Idea brief | List of research lanes, each with its own question |
| Research (×N) | Gathers evidence for one lane | One research lane | Findings + sources for that lane |
| Skeptic | Adversarially reviews all findings, kills unsupported claims | All research findings | Surviving (verified) claims only |
| Merge | Synthesizes survivors into a recommendation | Surviving claims | One-page recommendation |
| Human Gate | Presents recommendation + next-move menu, captures the decision | Recommendation | Human's chosen next action |
| Supervisor | Cross-cutting — logs/monitors every agent above, doesn't sit in the linear flow | All agent I/O | Run logs, timing, failure reports |

## Tech Stack

Decided (2026-08-22):

- **Python** — primary language for the backend (agents, tools, API).
- **FastAPI** — serves the pipeline: `POST /runs` (start), `GET /runs/{id}` (status),
  `POST /runs/{id}/respond` (feed a human answer into a paused Intake or Human Gate
  interrupt). Streams progress via SSE (`StreamingResponse`) rather than polling.
- **LangGraph** — orchestrates the agent graph:
  - `StateGraph` with one node per stage (Intake, Plan, Research, Skeptic, Merge,
    Human Gate), matching `workflows/` 1:1.
  - `Send` API for the Plan → Research fan-out (Planner returns N lanes, LangGraph
    spawns one Research node per lane in parallel, fans back in automatically).
  - `interrupt()` for Intake's back-and-forth and Human Gate's decision — pauses the
    graph and resumes on the next human input instead of hand-rolled state machines.
  - Checkpointer for persistence across interrupts (a paused run must survive a
    server restart). Start with `SqliteSaver`; swap to a Postgres checkpointer only
    if/when multi-user or heavier concurrency needs it.
  - Plain LangChain chain abstractions are skipped for simple "prompt in, text out"
    calls — those go straight through the model client. LangChain is only pulled
    in where LangGraph's prebuilt agent helpers need a LangChain-wrapped model (e.g.
    a Research lane agent that loops on tool calls itself).
- **LLM: model-agnostic, Claude by default** (`claude-opus-5-5` via the official
  `anthropic` SDK). Nodes never touch a vendor SDK — they call one function,
  `graph/llm.py::generate_structured(prompt, Schema, effort=...)`, which returns a
  validated Pydantic instance (never free-text parsing). Which vendor answers is
  configuration: `LLM_PROVIDER`, `LLM_MODEL`, `LLM_MAX_TOKENS`. Key: `ANTHROPIC_API_KEY`.
  - The seam is `graph/providers/base.py::LLMProvider`: one method,
    `complete_structured(...)`. Adding a provider = one file in `graph/providers/` +
    one `register_provider(...)` call; no node changes. Only Anthropic exists today.
  - `effort` (`"low"|"medium"|"high"`) is the provider-neutral reasoning dial; each
    provider maps it onto its own mechanism.
  - Multi-turn is the caller's job (Intake renders its transcript into the prompt), so
    nothing assumes a provider keeps conversation state server-side.
  - Keep response schemas simple — no unions beyond `Optional`, no recursion — the
    lowest common denominator across structured-output implementations.
  - Failures are typed (`LLMRefusalError`, `LLMTruncatedError`, `LLMEmptyResponseError`)
    and surface as a failed run with the reason, never an empty result.
  - LangChain is **not** used as a model wrapper; LangGraph orchestrates plain Python
    functions, so the extra layer bought nothing.
- **Firecrawl** — web search + scrape/extract tool for the Research lanes. Chosen
  over Tavily: same "give an LLM agent clean, citation-ready content" niche, but
  Firecrawl also covers full-page scrape/crawl in one tool, reducing the need for a
  separate scraping tool.
- **Persistence** — SQLite for run/checkpoint state to start (single deploy, no
  external DB dependency). `logs/` stays separate as the Supervisor's
  human-readable, append-only audit trail (not the same store as LangGraph's
  checkpointer).
- **Frontend: Next.js (App Router) + TypeScript**, Tailwind + shadcn/ui. Even though
  this is meant to become a real product for other people eventually, **no auth for
  now** — single-deploy, no login wall, add auth later if/when multi-tenancy is
  actually needed. Key UI surfaces:
  - Streaming chat view for Intake (Vercel AI SDK `useChat` or plain
    EventSource against the FastAPI SSE endpoint).
  - A distinct Human Gate card (recommendation + next-move buttons), not just
    another chat bubble — it shouldn't get lost in scroll.
  - A run list/dashboard (status: in progress / awaiting human / done).

Build order: (1) LangGraph pipeline + FastAPI, exercised via curl/Postman — prove
Intake interrupt → Plan → parallel Research → Skeptic → Merge → Human Gate interrupt
works end to end before any UI; (2) Next.js frontend against the stable API; (3)
Supervisor logging/cost dashboard.

**Nothing above is built yet.** This file and `workflows/` define the target
architecture. Implementation starts only when explicitly asked for.

## The WAT Architecture

This project follows **WAT** (Workflows, Agents, Tools): separate concerns so
probabilistic reasoning (the agents above) and deterministic execution (code) don't
get tangled together.

**Layer 1: Workflows (The Instructions)**
- Markdown SOPs in `workflows/` — one per agent/stage in the graph above.
- Each workflow defines: objective, required inputs, which tools to use, expected
  output, and how to handle edge cases.
- Written in plain language, the same way you'd brief someone on the team.

**Layer 2: Agents (The Decision-Makers)**
- Each role in the table above is an agent: it reads its workflow, calls tools in the
  right order, handles failures, and (for Intake and Human Gate) talks to the human.
- Agents connect intent to execution without trying to do everything themselves.
- Example: the Research agent for the "Competitors" lane doesn't scrape a site by
  hand — it reads `workflows/research_lane.md`, figures out the required inputs, then
  calls a tool in `tools/`.

**Layer 3: Tools (The Execution)**
- Python scripts in `tools/` that do the actual work: web search/scraping, structured
  data extraction, persistence, notifications.
- API keys and credentials live in `.env` — never anywhere else.
- Deterministic, testable, fast — this is where reliability comes from.

**Why this matters:** if every step in a 5+ stage pipeline is handled by an LLM
guessing at execution, small per-step error rates compound fast (90% accuracy per
step → 59% success after five steps). Pushing execution into deterministic tools is
what keeps a graph this deep reliable.

## How to Operate (for whoever/whatever is coordinating this repo)

**1. Look for existing tools first.** Check `tools/` before writing a new script.
Only build new tools when nothing covers the task.

**2. Learn and adapt when things fail.**
- Read the full error and trace.
- Fix the tool and retest (check in first if it burns paid API calls/credits before
  re-running).
- Document what was learned in the relevant workflow file (rate limits, timing
  quirks, unexpected behavior).

**3. Keep workflows current, but don't rewrite them silently.** Workflows evolve as
better methods or constraints are discovered. Don't create or overwrite a workflow
file without asking, unless explicitly told to — these are living instructions, not
scratch notes.

## The Self-Improvement Loop

1. Identify what broke.
2. Fix the tool.
3. Verify the fix works.
4. Update the workflow with the new approach.
5. Move on with a more robust system.

## How This Gets Built — Multiple Coding Agents in Parallel

Four build sessions run concurrently. **Claude is the Lead**: it owns the contracts
and the wiring, writes each session's brief, and merges their work. The human
approves every task assignment before a build starts.

Hermes runs **three sessions** — same agent name, zero shared files.

| Session | Half of the project | Owns (creates) |
|---|---|---|
| **Lead** (Claude) | Contracts, wiring, human-in-the-loop | `graph/`, `api/`, `agents/intake.py`, `agents/human_gate.py`, `briefs/`, `docs/` |
| **Hermes · backend** | Evidence | `tools/*`, `agents/research.py`, its tests |
| **Hermes · frontend** | UI | `frontend/**` — no Python, ever |
| **Hermes · reasoning** | Reasoning | `agents/planner.py`, `agents/skeptic.py`, `agents/merge.py`, `agents/prompts/`, its tests |

The reasoning half was first assigned to a separate **Antigravity** session that
delivered nothing; it was reassigned to a third Hermes session. Ownership boundaries
are unchanged — only the executor.

The three rules that make parallelism actually work:

1. **Contracts are executable, not prose.** `graph/state.py` defines every node's
   input/output as Pydantic models; `docs/API_CONTRACT.md` does the same for the
   frontend. Both are written *before* anyone codes, both are Lead-only. An agent
   that violates one fails a type check, not a code review three days later.
2. **Ownership is by file, not by concept.** Each session creates new files in its own
   folders and **never edits a file it didn't create**. Shared files are Lead-only.
   Need a field that isn't in a contract? Stop and report — never edit locally.
3. **Every task is a written brief with an acceptance test.** A module that can't
   demonstrate it works in isolation doesn't get merged. The frontend proves itself
   against mocks; it never waits on — or calls — a live backend.

**Context layer** — read in this order before writing code:
`briefs/RULES.md` → `CLAUDE.md` → `docs/ARCHITECTURE.md` →
`graph/state.py` (Python sessions) or `docs/API_CONTRACT.md` (frontend session) →
your own `briefs/<SESSION>.md` → your stage's `workflows/*.md`.

## File Structure

```
CLAUDE.md       # This file — project context + operating instructions
docs/           # ARCHITECTURE.md (design) + API_CONTRACT.md (frozen, frontend builds on it)
briefs/         # RULES.md (all agents) + one task brief per build session
frontend/       # Next.js app — Hermes frontend session only. No auth.
workflows/      # Markdown SOPs, one per agent/stage in the graph
agents/         # Per-agent node implementations + prompts
tools/          # Python scripts for deterministic execution (search, scraping, extraction, etc.)
api/            # FastAPI app — kicks off runs, exposes status, serves the human gate
graph/          # Contracts (state.py), shared LLM factory (llm.py), graph wiring. LEAD-ONLY.
tests/          # Per-module tests. Must pass offline — no live API, no live LLM.
logs/           # Supervisor output — run logs, timing, failure reports
.tmp/           # Temporary/intermediate files (scraped data, draft outputs). Disposable.
.env            # API keys and environment variables (NEVER store secrets anywhere else)
```

**Core principle:** local files under `.tmp/` and `logs/` are for processing and
observability. Anything the human needs to act on — the recommendation, the human
gate decision — should be easy to surface, not buried in intermediate files.

## Bottom Line

Six agents plus a supervisor, wired as a graph, turning a vague idea into a decision
a human actually makes. Stay pragmatic about what's an agent's job (judgment) versus
a tool's job (execution). Keep the workflows honest as the system learns.
