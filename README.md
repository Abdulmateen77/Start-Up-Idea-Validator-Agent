# Idea Validator Agent

![Python](https://img.shields.io/badge/python-3.13-3776AB?logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-3.7%20Flash-8E75B2?logo=googlegemini&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-orchestration-1C3C3C)
![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=nextdotjs&logoColor=white)
![Tests](https://img.shields.io/badge/tests-52%20passing-brightgreen)

Turns "should we build X?" into a one-page, evidence-backed recommendation — then
makes a **human** decide what happens next, not the model.

A vague sentence goes in. It gets sharpened into a researchable brief, split into
parallel research lanes, and every claim that comes back is attacked by a Skeptic
agent whose only job is to kill what doesn't hold up. What survives becomes a
one-pager. The model never gets to make the call — it hands the human a decision,
with the evidence and the gaps both left visible.

## Pipeline

```
INTAKE ⇄ human       vague idea  →  specific niche + audience + one core question
   ↓
PLAN                 core question  →  N independent research lanes (never fixed)
   ↓  ⇉ fan out
RESEARCH ×N           one agent per lane, in parallel — every claim carries a source
   ↓  ⇉ fan in
SKEPTIC               attacks every claim; unsupported ones don't survive
   ↓
MERGE                 survivors only → one-page recommendation, caveats intact
   ↓
HUMAN GATE ⇄ human    tailored next-move menu — human picks, or sends a lane back
```

A **Supervisor** runs alongside the graph, not inside it — logging every agent's
input, output, timing, and failures for observability.

## Why it's built this way

- **Every stage is structured output.** A Pydantic schema in, a validated instance
  out — never free-text parsed. This is what lets a 6-stage pipeline stay reliable:
  compounding errors from an LLM guessing at formatting is the usual failure mode
  for graphs this deep.
- **Killed claims are structurally excluded, not just prompted away.** Merge never
  even sees a claim the Skeptic killed — it's filtered out of the prompt before the
  model runs, so a bad claim can't leak back in by the model "forgetting" an instruction.
- **Human-in-the-loop stages are two LangGraph nodes each**, not one. `interrupt()`
  re-executes a node from the top on resume — so if a single node both called the LLM
  and interrupted, every human reply would burn a duplicate paid call. The LLM work
  and the interrupt are split apart.
- **Multi-turn Intake is stateless on this side.** Gemini 3.7's Interactions API
  holds conversation history server-side via `previous_interaction_id` — no
  transcript gets resent, no context window creep from a long back-and-forth.

## Stack

| | |
|---|---|
| LLM | Gemini 3.7 Flash, via `google-genai`'s Interactions API |
| Orchestration | LangGraph — `Send` fan-out, `interrupt()`, SQLite checkpointing |
| Research | Firecrawl (search + scrape) |
| API | FastAPI — REST + SSE, see [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) |
| Frontend | Next.js 15, no auth |

Full design rationale: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Per-stage
specs: [`workflows/`](workflows/).

## Quickstart

```bash
py -3.13 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS/Linux

cp .env.example .env   # fill in GEMINI_API_KEY + FIRECRAWL_API_KEY

.venv/Scripts/python.exe -m uvicorn api.main:app --reload
```

```bash
curl -X POST localhost:8000/runs -H 'content-type: application/json' \
     -d '{"raw_idea":"AI bookkeeping for Shopify sellers"}'
# → awaiting_human, Intake's first question

curl -X POST localhost:8000/runs/$ID/respond -H 'content-type: application/json' \
     -d '{"kind":"intake_answer","message":"solo operators doing $10-100k/mo"}'
# repeat until Intake has enough to build a brief — the loop is unbounded by design

curl localhost:8000/runs/$ID          # full state
curl localhost:8000/runs/$ID/stream   # SSE
```

`status` (`running` / `awaiting_human` / `done` / `failed`) is derived server-side —
no client ever infers whether a run is paused. Polling alone is always correct; SSE
is a liveness layer on top, not a second source of truth.

Frontend: `cd frontend && npm install && npm run dev` — point it at a live backend
with `NEXT_PUBLIC_API_BASE=http://localhost:8000`, or leave it unset to run against
its own bundled mocks.

## Tests

```bash
.venv/Scripts/python.exe -m pytest
```

52 tests, 100% offline — no live LLM or Firecrawl call anywhere in the suite. Every
paid call is mocked at its own import site, down to full HTTP-level integration
tests that drive the real FastAPI app through the real compiled graph.

## Status

Every node is real and wired end to end; the full graph compiles and runs with no
stubs. Live-fire proven against real Gemini calls at the Intake stage; a complete
live run through Research → Skeptic → Merge → Human Gate is the next milestone.

## Built by four sessions in parallel

Contracts first, execution second: [`graph/state.py`](graph/state.py) (Python) and
[`docs/API_CONTRACT.md`](docs/API_CONTRACT.md) (frontend) were frozen before any
node was written, so four sessions could build concurrently in one working tree
without colliding — disjoint file ownership, no shared edits, a session that needs
something outside its contract stops and reports rather than guessing.
See [`briefs/RULES.md`](briefs/RULES.md).
