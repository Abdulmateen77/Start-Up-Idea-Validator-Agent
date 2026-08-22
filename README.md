# Idea Validator Agent

Turns a vague idea into a one-page, evidence-backed recommendation — and then makes a
human decide what to do about it.

Six agents wired as a graph. A vague sentence goes in, gets sharpened into a
researchable brief, split into parallel research lanes, attacked by a skeptic that
kills unsupported claims, synthesized into one page, and handed to a human with a
menu of next moves. **The model never makes the call.**

## The pipeline

```
INTAKE ⇄ human        turn a vague idea into a specific niche + audience + one question
   ↓
PLAN                  decompose into research lanes (chosen per-idea, never fixed)
   ↓  ⇉ fan out
RESEARCH ×N           one agent per lane, in parallel, every claim carries a source
   ↓  ⇉ fan in
SKEPTIC               attacks every claim; weak ones don't survive; gaps are recorded
   ↓
MERGE                 survivors become a one-page recommendation, caveats intact
   ↓
HUMAN GATE ⇄ human    tailored next-move menu — the human picks, or sends a lane back
```

A **Supervisor** runs alongside rather than inside the flow, logging every agent's
I/O, timing, failures and cost.

Design details live in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md); the per-stage
SOPs are in [workflows/](workflows/).

## Stack

- **Gemini 3.7 Flash** via the `google-genai` **Interactions API**. Every node uses
  structured output — a Pydantic schema in, a validated instance out. No free-text
  parsing anywhere.
- **LangGraph** for orchestration: `Send` for the research fan-out, `interrupt()` for
  the two human-in-the-loop stages, SQLite checkpointing so a run paused on a human
  survives a restart.
- **FastAPI** — see [docs/API_CONTRACT.md](docs/API_CONTRACT.md).
- **Next.js** frontend. No auth, deliberately.
- **Firecrawl** for search and scrape.

## Setup

```bash
py -3.13 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt  # macOS/Linux

cp .env.example .env      # then fill in GEMINI_API_KEY and FIRECRAWL_API_KEY
```

Secrets go in `.env` and nowhere else. `.env` is gitignored; `.env.example` holds
empty placeholders and *is* committed.

## Run

```bash
.venv/Scripts/python.exe -m uvicorn api.main:app --reload
```

```bash
# start a run — comes back awaiting_human with Intake's first question
curl -X POST localhost:8000/runs -H 'content-type: application/json' \
     -d '{"raw_idea":"AI bookkeeping for Shopify sellers"}'

# answer it (repeat until Intake has a brief — the loop is unbounded by design)
curl -X POST localhost:8000/runs/$ID/respond -H 'content-type: application/json' \
     -d '{"kind":"intake_answer","message":"solo operators doing $10-100k/mo"}'

curl localhost:8000/runs/$ID          # full state
curl localhost:8000/runs/$ID/stream   # SSE liveness
```

`status` is derived server-side (`running` / `awaiting_human` / `done` / `failed`) so
no client ever has to infer whether a run is paused. Polling is always correct; SSE is
a liveness optimisation layered on top.

## Tests

```bash
.venv/Scripts/python.exe -m pytest
```

All tests run **offline** — no live LLM, no live Firecrawl. Anything that would spend
money is mocked.

## How this repo is built

Four sessions work in parallel in one tree, so correctness rests on disjoint file
ownership plus two frozen contracts — `graph/state.py` for Python,
`docs/API_CONTRACT.md` for the frontend. Both are Lead-only; a session needing a field
that isn't there stops and reports rather than editing.

See [briefs/RULES.md](briefs/RULES.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
