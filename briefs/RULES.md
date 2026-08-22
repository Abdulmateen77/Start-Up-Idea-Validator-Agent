# Rules for all coding agents

Applies to **Hermes** and **Antigravity**. The Lead follows them too.
Read this, then `CLAUDE.md`, then `docs/ARCHITECTURE.md`, then your own brief.

---

## 0. Environment — read before you run anything

**Use the project venv at `.venv/`. It already exists, created with Python 3.13.**

```
.venv/Scripts/python.exe -m pytest        # Windows
.venv/Scripts/python.exe -m pip install   # only with Lead approval
```

Two traps, both already hit once:

- **Bare `python` on PATH is NOT this project.** On this machine it resolves to
  `AppData\Local\hermes\hermes-agent\venv\python.exe` — the Hermes *agent's own*
  runtime, which has no pip. Installing there pollutes another agent's environment
  and your imports will fail in confusing ways. Always use `.venv/Scripts/python.exe`.
- **Do not create your own venv.** All sessions share one working tree; a second
  environment means your tests pass against different package versions than the
  Lead's, and "works for me" becomes unfalsifiable.

Dependencies live in `requirements.txt` (Lead-owned). Need a new one? Report it.

---

## 1. Stay in your lane (literally)

- Create **new files** in **your assigned folders only**. Your brief names them.
- **Never edit a file you did not create.** Not to fix a typo, not to add an import.
- If another agent's file is wrong or blocking you: **report it to the Lead**. The
  Lead merges and reconciles. Two agents editing one file is the failure mode this
  whole structure exists to prevent.

## 2. `graph/state.py` is frozen

- Import your types from it. Never modify it.
- Need a field that isn't there? **Stop. Report to the Lead.** Do not add it locally.
  A local schema edit compiles fine for you and breaks at integration — that is the
  single most expensive bug this project can have.
- Same for `graph/llm.py`. Import `get_llm`. Don't build your own client.

## 3. Every node returns a partial dict

```python
def some_node(state: RunState) -> dict:
    return {"lanes": [...], "events": [event]}   # ✅ only what you set
```

Never return the whole state. Never mutate the input state in place.
`events` is always a **list**, even with one item — a reducer concatenates it.

## 4. Structured output only

```python
from graph.llm import generate_structured

result = generate_structured(prompt, ResearchPlan)          # ✅ validated instance
result = json.loads(some_raw_model_reply)                    # ❌
```

No regex over model output. No free-text parsing. No "the model usually returns JSON."

Gemini 3.7 specifics that will bite you if ignored:

- **`temperature` / `top_p` / `top_k` are removed in 3.7.** Passing them errors. Use
  `thinking_level="low"|"medium"|"high"` instead — that's the reasoning-effort dial.
- **Response schemas may not contain union types** other than `Optional`. No `A | B`.
- Do not build your own `genai.Client`. Import from `graph.llm`.

## 5. Fail loudly

- Tool failures raise a typed error and get recorded as a `ToolFailure`.
- **Never return an empty result as if nothing went wrong.** An empty research lane
  and a broken scraper look identical downstream — that's how a silent failure
  becomes a confident wrong recommendation.
- "No evidence found" is a real finding: set `no_evidence_found=True`. That is
  different from a failure, and both are different from silently returning `[]`.

## 6. Tests are part of the deliverable

- Every module ships with a test that runs standalone.
- **`tools/` tests must not call a live API or an LLM.** Mock the HTTP layer.
  A test suite that costs money or needs network doesn't get run, so it doesn't work.
- Agent-node tests: mock `get_llm` and assert the node returns the right shape.
  You are testing wiring and contract compliance, not model quality.

## 7. Money and secrets

- **Never commit a secret.** Real keys live in `.env` (gitignored) and nowhere else.
  `.env.example` holds empty placeholders only.
- Read config with `os.getenv`. Never hardcode a key, not even temporarily.
- **Do not run anything that burns paid API credits without checking in first.**
  Firecrawl and Gemini both cost money. Build against mocks; ask before a live run.

## 8. Match the codebase

- Python 3.11+, type hints on every public function, `from __future__ import annotations`.
- Docstrings explain **why**, not what. Comment density matching `graph/state.py`.
- Your workflow file in `workflows/` is the spec for your node's behaviour. If your
  code and the workflow disagree, the workflow wins — or you report the conflict.
- Don't invent abstractions for one caller. No base classes "for later."

## 9. Report back in this format

When your brief is done, reply with exactly these five sections:

```
BUILT:        files created, one line each
CONTRACT:     any place graph/state.py didn't fit — or "clean"
ASSUMED:      decisions you made that the brief didn't cover
NOT DONE:     anything in the brief you couldn't complete, and why
TO VERIFY:    what the Lead should check first
```

Do not report a task as done if its tests don't pass. Say what failed and show the
output. A truthful "3 of 5 done" is worth more than a false "complete" — the Lead is
integrating your work with two other agents' and will find out either way.

## 10. Don't scope-creep

Build what your brief says. If you spot something outside it that needs doing, put it
in `ASSUMED` or `TO VERIFY` and let the Lead assign it. Do not helpfully build the
next agent's module.
