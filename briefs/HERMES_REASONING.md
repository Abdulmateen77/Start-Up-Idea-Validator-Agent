# Brief — HERMES · REASONING SESSION

> **Reassigned work.** This was originally the Antigravity session's brief. That
> session produced nothing at all, so the three reasoning nodes are now yours. Nothing
> exists for them — you are starting from an empty slate, not fixing someone's work.
>
> Two other Hermes sessions already delivered: the **backend** session
> (`tools/`, `agents/research.py`) and the **frontend** session (`frontend/`). Their
> work is merged and committed. **Do not touch either.**

**Your half of the project: reasoning.** The three pure-thinking nodes — no tool
calls, no human interrupts, no network. State in, structured judgement out.

That constraint is the point: your nodes are fully testable with a mocked LLM, and
none of them can be broken by a flaky scraper.

**Read first:** `briefs/RULES.md` → `CLAUDE.md` → `docs/ARCHITECTURE.md` →
`graph/state.py` → `workflows/02_plan_research_lanes.md`,
`04_skeptic_review.md`, `05_merge_recommendation.md`

**Read `agents/research.py` too.** It's a finished, merged node by another session —
the clearest worked example of the shape yours must take.

---

## Environment

Use the existing project venv. **Do not create your own, and do not use bare
`python`** — on this machine that resolves to the Hermes *agent's* runtime, which has
no pip and is not this project.

```
.venv/Scripts/python.exe -m pytest
```

Everything you need is already installed. `requirements.txt` is Lead-owned.

---

## Files you own — create these, nothing else

```
agents/planner.py
agents/skeptic.py
agents/merge.py
agents/prompts/__init__.py
agents/prompts/planner.py       # prompt text as module constants
agents/prompts/skeptic.py
agents/prompts/merge.py
tests/test_agents_planner.py
tests/test_agents_skeptic.py
tests/test_agents_merge.py
```

**Do not touch:** `graph/`, `api/`, `tools/`, `frontend/`, `agents/research.py`,
`agents/intake.py`, `agents/human_gate.py`.

Keep prompt text in `agents/prompts/` as plain constants, separate from node logic.
Prompts change often; wiring shouldn't churn with them.

---

## Two traps that have already cost this project real time

**1. Read the event AFTER the `with` block, never inside it.**

`tools/run_logger.track()` only populates `holder.event` in its `finally` clause. Read
it inside the block and you get `None` — your node returns an empty `events` list, the
Supervisor goes blind to your entire stage, and **every test still passes unless you
assert on it**. This exact bug shipped in two different nodes already.

```python
with track(run_id=run_id, agent="Planner", stage=Stage.PLAN, input_summary=summary) as holder:
    ...
    holder.output_summary = f"produced {len(lanes)} lanes"
    # ❌ event_obj = getattr(holder, "event", None)   <- always None here

event_obj = getattr(holder, "event", None)           # ✅ after the block
return {"lanes": lanes, "stage": Stage.RESEARCH, "events": [event_obj] if event_obj else []}
```

Assert `len(result["events"]) == 1` in every one of your tests.

**2. Keep response schemas simple** — no union types beyond `Optional` (no `A | B`
fields), no recursion. The LLM layer is provider-agnostic, so that is the lowest
common denominator. There are no sampling params either; the reasoning dial is
`effort`.

---

## Task 1 — `agents/planner.py`

```python
def plan_node(state: RunState) -> dict:
    # reads  state["brief"]
    # returns {"lanes": [...], "stage": Stage.RESEARCH, "events": [AgentEvent(...)]}
```

Follow `workflows/02_plan_research_lanes.md`. The parts that matter most:

- **Lanes are decided per-idea, never fixed.** Customer Pain / Competitors /
  Distribution are *examples from one reference idea*, not a template. An idea needing
  Regulatory or Unit Economics should get those. Do not hardcode a default set and do
  not force-fit three lanes.
- 2 lanes is fine. 5 is fine. Don't pad to hit a number.
- Each lane's question must be **specific and answerable**, not a restatement of
  `core_question`.
- **Lanes must be independent** — they run in parallel. If lane B's question can only
  be answered after lane A's, they aren't independent: merge them into one lane.
  Encode this in the prompt explicitly; it's the failure mode this stage has.

**Tag each lane with a `LaneArchetype`.** This selects the research *playbook* the
single Research agent uses (see `tools/playbooks.py`, already built). Two rules:

- Tag by **research method**, not topic keyword. A lane called "Pricing Pressure"
  meaning "what do rivals charge" is `COMPETITORS`, not `UNIT_ECONOMICS`.
- **`OTHER` is a first-class answer, not a failure.** Invent the lane the idea
  actually needs and tag it `OTHER` if nothing fits. Never distort a lane's question
  to make it match an archetype — the archetype serves the lane, not the reverse.

Use `generate_structured(prompt, ResearchPlan)` from `graph.llm`.

## Task 2 — `agents/skeptic.py`

```python
def skeptic_node(state: RunState) -> dict:
    # reads  state["findings"], state["brief"], state["lanes"]
    # returns {"skeptic_report": SkepticReport(...), "stage": Stage.MERGE, "events": [...]}
```

Follow `workflows/04_skeptic_review.md`. This node's entire job is attacking evidence —
it is not a light pass. For each claim ask:

- Is the source credible, and does it actually say what the claim says it says?
- Is a single data point being treated as a trend?
- Does it contradict a claim from a different lane?
- Is it relevant to `core_question`, or scope creep?

Rules that are easy to get wrong:

- Three verdicts, not two: `SURVIVES`, `SURVIVES_WITH_CAVEAT`, `KILLED`.
  `reason` is required on **all three**. `caveat` is required when caveated.
- A claim that's plausible but genuinely unverifiable → `SURVIVES_WITH_CAVEAT`.
  **Don't kill it just because verification is hard** — but don't let it pass clean either.
- Claims arriving with `unsourced=True` are not auto-killed. Judge them.
- **Gaps are output, not failure.** A Plan question no lane answered credibly goes in
  `gaps`. Never invent a claim to fill one.
- **If almost everything gets killed, report that plainly.** Do not soften the report
  to make the pipeline look productive. That outcome is the system working.

Cross-lane contradiction detection means the prompt needs *all* findings at once —
don't loop claim-by-claim in isolation.

Use `effort="high"`.

## Task 3 — `agents/merge.py`

```python
def merge_node(state: RunState) -> dict:
    # reads  state["skeptic_report"], state["brief"]
    # returns {"recommendation": Recommendation(...), "stage": Stage.HUMAN_GATE, "events": [...]}
```

Follow `workflows/05_merge_recommendation.md`. One page, readable in under a minute.

- Restate `core_question` at the top. Group findings by lane. Lead with what most
  directly bears on the core question.
- **Only `SURVIVES` and `SURVIVES_WITH_CAVEAT` claims may appear.** Killed claims must
  not leak back in. Caveats travel *with* their claim — don't strip them for brevity.
- Carry Skeptic's `gaps` through to `Recommendation.gaps`.
- **Never manufacture confidence.** "Not enough evidence yet, here's what's missing"
  is a legitimate, useful verdict.
- Evidence pointing different directions across lanes (strong pain *and* crowded
  competition) → **surface the tension explicitly**. Do not average it into a mushy
  middle.
- **No next-move menu here.** That's Human Gate's job, and it's already built.

Use `effort="high"`.

## Task 4 — tests

Mock `graph.llm.generate_structured` in all three. You are testing **wiring and
contract compliance**, not model quality. **No test may call a real LLM.**

- `test_agents_planner.py` — returns `{"lanes", "stage", "events"}`; handles a 2-lane
  and a 5-lane plan without special-casing; a lane tagged `OTHER` passes through
  untouched.
- `test_agents_skeptic.py` — all three verdicts round-trip; `caveat` present on
  caveated claims; `gaps` populated; an all-killed report is returned as-is, not
  softened or emptied.
- `test_agents_merge.py` — **killed claims never appear in the output** (assert this
  explicitly, it's the highest-value test you'll write); caveats survive into
  `FindingGroup.points`; gaps carry through.
- **All three** — assert `len(result["events"]) == 1`. See trap 1 above.

---

## Definition of done

- All 10 files exist; `.venv/Scripts/python.exe -m pytest` passes offline.
- The existing 23 tests still pass — you should not have affected them.
- All three nodes return exactly the contract shapes above, `events` a single-item list.
- Nothing outside your file list was created or modified.
- Report back in the 5-section format in `briefs/RULES.md` §9
  (BUILT / CONTRACT / ASSUMED / NOT DONE / TO VERIFY).

## Ask the Lead before you

- Add or change anything in `graph/state.py` (you may not — report instead).
- Run a live LLM call (**costs money**). Build against mocks.
- Add a dependency beyond what's in `requirements.txt`.
- Change a node's signature, or move work between the three stages.
- `git commit` — don't. The Lead reviews and commits.
