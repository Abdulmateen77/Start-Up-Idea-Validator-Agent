# Architecture — Idea Validator Agent

Read this **and** `CLAUDE.md` before writing any code. If this file and your brief
disagree, the brief wins for scope, this file wins for interfaces.

## The graph

```
                    ┌──────────────────────────────────────┐
   raw idea ──────► │ INTAKE          interrupt() ⇄ human   │  Lead
                    └──────────────┬───────────────────────┘
                                   │ IdeaBrief
                    ┌──────────────▼───────────────────────┐
                    │ PLAN            → list[ResearchLane] │  Antigravity
                    └──────────────┬───────────────────────┘
                                   │ Send() fan-out, one per lane
              ┌────────────────────┼────────────────────┐
              ▼                    ▼                    ▼
         ┌─────────┐          ┌─────────┐          ┌─────────┐
         │RESEARCH │          │RESEARCH │          │RESEARCH │   Hermes
         │ lane A  │          │ lane B  │          │ lane N  │
         └────┬────┘          └────┬────┘          └────┬────┘
              └────────────────────┼────────────────────┘
                                   │ fan-in via operator.add → list[LaneFindings]
                    ┌──────────────▼───────────────────────┐
                    │ SKEPTIC        → SkepticReport        │  Antigravity
                    └──────────────┬───────────────────────┘
                    ┌──────────────▼───────────────────────┐
                    │ MERGE          → Recommendation       │  Antigravity
                    └──────────────┬───────────────────────┘
                    ┌──────────────▼───────────────────────┐
                    │ HUMAN GATE      interrupt() ⇄ human   │  Lead
                    └──────────────────────────────────────┘

   SUPERVISOR ── not a node. Every node appends AgentEvent to state["events"].
```

## Layer map (WAT)

| Layer | Lives in | Who |
|---|---|---|
| Workflows — the SOPs | `workflows/*.md` | already written, read yours |
| Agents — decision-makers | `agents/*.py` | Hermes + Antigravity + Lead |
| Tools — deterministic execution | `tools/*.py` | Hermes |
| Contracts + wiring | `graph/*.py` | **Lead only** |
| API | `api/*.py` | **Lead only** |

## Ownership — who writes what

Four build sessions run in parallel. Hermes runs **two** — they share an agent name
but share no files.

| Session | Creates | Must never touch |
|---|---|---|
| **Lead** | `graph/`, `api/`, `agents/intake.py`, `agents/human_gate.py`, `briefs/`, `docs/` | — |
| **Hermes · backend** | `tools/*`, `agents/research.py`, `tests/test_tools_*.py`, `tests/test_agents_research.py` | `graph/`, `api/`, `frontend/`, `agents/` except `research.py` |
| **Hermes · frontend** | `frontend/**` — the entire Next.js app | everything outside `frontend/` — no `.py` files at all |
| **Antigravity** | `agents/planner.py`, `agents/skeptic.py`, `agents/merge.py`, `agents/prompts/`, `tests/test_agents_*.py` | `graph/`, `api/`, `tools/`, `frontend/`, `agents/research.py` |

Split rationale: Hermes-backend owns the **evidence half** (tools + the one node that
calls them), Antigravity owns the **reasoning half** (three pure-reasoning nodes, no
tool calls, no interrupts), Hermes-frontend owns the **entire UI** and no Python.
Lead owns everything shared plus the two human-in-the-loop nodes — those are the ones
most likely to force a state-schema change, and the Lead owns the schema.

**Two frozen contracts, two audiences.** `graph/state.py` is the contract for the
Python sessions. `docs/API_CONTRACT.md` is the contract for the frontend session —
it builds entirely against mocks and never calls a live backend. Both are Lead-only.

## Node signatures — FROZEN

Every node takes state, returns a **partial dict** (only the keys it sets).
Never return the whole state. Never mutate the input.

```python
# agents/intake.py        — Lead
def intake_node(state: RunState) -> dict: ...

# agents/planner.py       — Antigravity
def plan_node(state: RunState) -> dict:
    # reads: state["brief"]
    # returns: {"lanes": [...], "stage": Stage.RESEARCH, "events": [AgentEvent(...)]}

# agents/research.py      — Hermes
def research_node(task: LaneTask) -> dict:
    # NOTE: receives LaneTask (one lane), NOT RunState. It is fanned out via Send().
    # returns: {"findings": [LaneFindings(...)], "events": [AgentEvent(...)]}
    #          ^ single-item list — the operator.add reducer concatenates across lanes

# agents/skeptic.py       — Antigravity
def skeptic_node(state: RunState) -> dict:
    # reads: state["findings"], state["brief"], state["lanes"]
    # returns: {"skeptic_report": SkepticReport(...), "stage": ..., "events": [...]}

# agents/merge.py         — Antigravity
def merge_node(state: RunState) -> dict:
    # reads: state["skeptic_report"], state["brief"]
    # returns: {"recommendation": Recommendation(...), "stage": ..., "events": [...]}

# agents/human_gate.py    — Lead
def human_gate_node(state: RunState) -> dict: ...
```

`events` is always a **single-item list** — the `operator.add` reducer appends it.
Returning a bare `AgentEvent` (not wrapped in a list) will break the reducer.

## One Research agent, N lanes — not one agent per lane

The worked example shows Customer Pain / Competitors / Distribution side by side.
Those are **three invocations of one agent**, not three agents. There is exactly one
`research_node`; `Send` fans it out once per lane the Planner produced.

Hardcoding a lane per agent would kill the Planner — it could only ever pick from a
fixed set, and an idea needing Regulatory or Unit Economics would get nothing.

What *does* legitimately differ per lane is **method**: Competitors wants vendor
pricing pages, Customer Pain wants forums and reviews, Distribution wants CAC data.
That variation lives in `tools/playbooks.py` as **data**, selected by
`ResearchLane.archetype` — not as branches in the node.

```
Planner  → tags each lane with a LaneArchetype (OTHER when nothing fits)
Research → get_playbook(archetype) → strategy + preferred_sources + query_hints
```

`LaneArchetype.OTHER` is the generic fallback and it is load-bearing: it's what keeps
lanes open-ended, so the Planner can invent a lane nobody anticipated and still get
good research. Adding an archetype is an optimisation, never a precondition for a
lane to exist.

## Shared infrastructure — import, don't rebuild

```python
from graph.state import RunState, IdeaBrief, ResearchLane, ...  # all contracts
from graph.llm import get_llm, FAST_MODEL                        # Gemini factory
```

- **One LLM factory.** Do not construct `ChatGoogleGenerativeAI` yourself.
- **Structured output always.** `get_llm().with_structured_output(SomeModel)`.
  No free-text parsing, no regex over model output, no `json.loads` on a raw reply.
- **One logging helper** (`tools/run_logger.py`, Hermes builds it). Once it exists,
  every node uses it to build its `AgentEvent`.

## Tech stack

Python 3.11+ · FastAPI · LangGraph (`StateGraph`, `Send`, `interrupt`, `SqliteSaver`)
· Gemini via `langchain-google-genai` · Firecrawl for search + scrape · SQLite ·
Next.js frontend (phase 2, no auth).

## Build phases

1. **Contracts + skeleton** (Lead) — `graph/state.py`, `graph/llm.py`, wiring stubs. ← done
2. **Parallel build** — Hermes and Antigravity work their briefs. Lead builds Intake,
   Human Gate, wiring, API.
3. **Integration** — Lead merges, runs the graph end to end via curl. No frontend yet.
4. **Frontend** — Next.js against the stable API.
5. **Supervisor dashboard** — logs + cost surfaced in the UI.

Nothing is merged until the graph runs end to end on a real idea.
