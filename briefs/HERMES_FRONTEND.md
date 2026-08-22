# Brief — HERMES · FRONTEND SESSION

> **You are the frontend Hermes session.** A second Hermes session
> (`briefs/HERMES_BACKEND.md`) is working the Python tool layer **at the same time**.
> You share an agent name; you do **not** share files.
>
> **You own `frontend/` and nothing else.** You may not create or edit a single `.py`
> file. If you think you need to touch backend code, you're wrong — report to the Lead.

**Read first:** `briefs/RULES.md` → `CLAUDE.md` → **`docs/API_CONTRACT.md`** →
`docs/ARCHITECTURE.md` (for context only — you implement none of it)

`docs/API_CONTRACT.md` is your `state.py`. It is frozen. Build against it.

---

## Hard constraint: there is no running backend

The API does not exist yet. **Do not wait for it, and do not call it.**

Build against a mock layer derived entirely from `docs/API_CONTRACT.md` — MSW
(Mock Service Worker) or Next.js route handlers under `frontend/src/mocks/`, your
call. Your mocks must be able to produce **every** state in the contract, including
the awkward ones:

- an Intake loop that asks 3 questions before producing a brief
- a 2-lane run *and* a 5-lane run
- a run whose lanes are **all `archetype: "other"`** — must look normal, not unstyled
- a lane with `no_evidence_found: true`
- a lane with `had_tool_failure: true`
- a `gate_decision` pause with 4 next-moves
- a `rerun_lane_id` decision sending the run backwards to `research`
- a `failed` run with a non-null `error`

If your UI only looks right on the happy path, it isn't done.

---

## Stack — fixed, don't substitute

Next.js (App Router) · TypeScript strict · Tailwind · shadcn/ui · **no auth**
(no login, no tokens, no user scoping — this is deliberate, not an oversight).

API base from `NEXT_PUBLIC_API_BASE`. Never hardcode a URL.

---

## Files you own

```
frontend/**            # the entire Next.js app — yours alone
```

Everything else in the repo is off limits. Do not add a root-level `package.json`,
do not touch `.gitignore`, do not edit `docs/` or `briefs/`.

---

## Task 1 — types + API client

- Hand-write `frontend/src/lib/types.ts` from `docs/API_CONTRACT.md`. The contract's
  TS block is copy-ready. Do not generate from a live server (there isn't one).
- A thin typed client: `createRun`, `listRuns`, `getRun`, `respond`, `streamRun`.
- **Polling must work standalone.** Implement `getRun` polling first and make the whole
  app correct on it. Then layer SSE on top as a liveness optimisation. A dropped SSE
  connection must never corrupt UI state — on any event, re-fetching is always valid.

## Task 2 — Intake chat view

Streaming conversation. `awaiting.kind === "intake_question"` → render the question
and an input; submit posts `{kind: "intake_answer", message}`.

- **The loop is unbounded.** Answering often returns another question. Normal, not an
  error. Never render "3 of 5 questions."
- Show prior `intake_turns` as history.
- Disable input while `status === "running"`.

## Task 3 — Pipeline progress view

Runs while `status === "running"` past intake. Drive it off `lane_progress`.

- **Lane count is dynamic** — 2 or 5, decided per-idea. Never hardcode three lanes and
  never assume the names Customer Pain / Competitors / Distribution.
- Show lanes running in parallel — this is the interesting part of the product, make
  it legible.
- `no_evidence_found` renders as a **legitimate result**, visually distinct from
  `had_tool_failure`, which renders as a **problem**. Do not collapse these into one
  "empty" state — that distinction is the whole point of the Skeptic stage upstream.

## Task 4 — Human Gate card

`awaiting.kind === "gate_decision"`. **Not a chat bubble** — a distinct, prominent
card. This is the moment the product exists for; it must not get lost in scroll.

- Render the full `Recommendation`: core question, findings grouped by lane, gaps,
  verdict.
- **Never truncate or summarise `FindingGroup.points`.** Caveats are inline in that
  text and two upstream agents worked to preserve them.
- Render `gaps` prominently — what's *missing* is as decision-relevant as what was found.
- A "not enough evidence yet" verdict is a **legitimate outcome**. Do not style it as
  an error or a failure.
- Next-moves: one button per `NextMove` (show `rationale`), plus a free-text custom
  move, plus a "re-run a lane" option that posts `rerun_lane_id`.
- After a `rerun_lane_id`, status returns to `running` and stage goes back to
  `research`. **The pipeline is not forward-only** — don't build a one-way stepper.

## Task 5 — Run dashboard

`GET /runs` list: idea, status, stage, updated time. Empty state. Click through to a
run. New-run entry point (`POST /runs`).

## Task 6 — verification

- `npm run build` and `tsc --noEmit` both clean. TypeScript strict, no `any`.
- A short `frontend/README.md`: how to run against mocks, how to point at a real API.
- Cover the state matrix above. Component tests are welcome but **the priority is that
  every contract state renders correctly** — screenshots or a mock-driven demo page
  are acceptable evidence.

---

## Definition of done

- App builds and typechecks clean; runs entirely on mocks with no backend.
- All four surfaces work: Intake chat, pipeline progress, Human Gate card, dashboard.
- Every state in the Task-1 matrix renders correctly, including reruns and failures.
- **Nothing outside `frontend/` was created or modified.**
- Report back in the 5-section format from `briefs/RULES.md` §9.

## Ask the Lead before you

- Anything that would need a field not in `docs/API_CONTRACT.md` (**report, don't invent**).
- Calling a real backend, or any paid API.
- Swapping a stack choice above.
- Creating any file outside `frontend/`.
