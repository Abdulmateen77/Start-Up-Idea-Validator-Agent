# API Contract — frozen

The frontend's equivalent of `graph/state.py`. The Next.js app is built against
**this document**, not against a running server.

**OWNERSHIP: Lead only.** If the frontend needs a field that isn't here, **stop and
report to the Lead** — do not invent it and do not scrape it out of `graph/state.py`.

Base URL comes from `NEXT_PUBLIC_API_BASE`. No auth — no tokens, no login, no user
scoping anywhere in v1.

---

## The one idea that matters: `status` is server-derived

The frontend must **never infer** whether a run is waiting on a human. The server
says so explicitly, and says what it's asking for.

```
status: "running" | "awaiting_human" | "done" | "failed"
```

`stage` tells you *where* in the pipeline. `status` tells you *whether the UI needs
to do something*. Render off `status` first, `stage` second. When
`status == "awaiting_human"`, the `awaiting` object is always non-null and tells you
exactly which UI to show.

---

## Types

```ts
type Stage = "intake" | "plan" | "research" | "skeptic" | "merge"
           | "human_gate" | "done" | "failed";

type Status = "running" | "awaiting_human" | "done" | "failed";

interface IdeaBrief { niche: string; audience: string; core_question: string; }

// Selects the backend research playbook. Useful in the UI for an icon or a subtle
// label — NEVER for layout logic. Treat it as a cosmetic hint with an open set:
// always handle "other", and never assume which archetypes a run will contain.
type LaneArchetype =
  | "customer_pain" | "competitors" | "distribution" | "regulatory"
  | "unit_economics" | "technical_feasibility" | "other";

interface ResearchLane {
  lane_id: string;
  name: string;
  question: string;
  archetype: LaneArchetype;
}

// Per-lane progress for the parallel fan-out. One entry per lane, live-updated.
interface LaneProgress {
  lane_id: string;
  name: string;
  archetype: LaneArchetype;
  state: "pending" | "running" | "done" | "failed";
  claim_count: number;
  no_evidence_found: boolean;
  had_tool_failure: boolean;
}

interface FindingGroup { lane_name: string; points: string[]; }

interface Recommendation {
  core_question: string;
  findings: FindingGroup[];
  gaps: string[];
  verdict: string;
}

interface NextMove { move_id: string; label: string; rationale: string; }

interface IntakeTurn { role: "agent" | "human"; content: string; }

interface HumanDecision {
  chosen_move_id: string | null;
  custom_note: string | null;
  rerun_lane_id: string | null;
}

// Discriminated union — switch on `kind` to pick the UI.
type Awaiting =
  | { kind: "intake_question"; question: string; turn_index: number }
  | { kind: "gate_decision"; recommendation: Recommendation; next_moves: NextMove[] };

interface RunView {
  run_id: string;
  status: Status;
  stage: Stage;
  raw_idea: string;
  created_at: string;          // ISO 8601 UTC
  updated_at: string;
  awaiting: Awaiting | null;   // non-null iff status === "awaiting_human"
  brief: IdeaBrief | null;
  intake_turns: IntakeTurn[];
  lanes: ResearchLane[];
  lane_progress: LaneProgress[];
  recommendation: Recommendation | null;
  human_decision: HumanDecision | null;
  error: string | null;        // non-null iff status === "failed"
}

interface RunSummary {          // dashboard list item
  run_id: string;
  status: Status;
  stage: Stage;
  raw_idea: string;
  created_at: string;
  updated_at: string;
}
```

---

## Endpoints

### `POST /runs` — start a run
```jsonc
// request
{ "raw_idea": "Should we build AI bookkeeping for Shopify?" }
// 201 → RunView
```
Returns immediately. The run will almost always come back
`status: "awaiting_human"` with an `intake_question` — Intake asks before it plans.

### `GET /runs` — dashboard list
```
200 → { "runs": RunSummary[] }    // newest first
```

### `GET /runs/{run_id}` — full state
```
200 → RunView
404 → { "detail": "run not found" }
```

### `POST /runs/{run_id}/respond` — answer a pause
Valid **only** when `status === "awaiting_human"`. Resumes the graph.

```jsonc
// when awaiting.kind === "intake_question"
{ "kind": "intake_answer", "message": "Solo operators doing $10-100k/mo" }

// when awaiting.kind === "gate_decision" — exactly ONE of these three
{ "kind": "gate_decision", "chosen_move_id": "customer_interviews" }
{ "kind": "gate_decision", "custom_note": "Talk to 5 merchants first" }
{ "kind": "gate_decision", "rerun_lane_id": "distribution" }
```
```
200 → RunView              // updated; may immediately be awaiting again
409 → { "detail": "run is not awaiting human input" }
422 → { "detail": "..." }  // wrong `kind` for the current pause
```

### `GET /runs/{run_id}/stream` — SSE
`text/event-stream`. Emits on every state change. Each `data:` is JSON.

```jsonc
{ "event": "stage_changed",  "stage": "research" }
{ "event": "lane_started",   "lane_id": "competitors", "name": "Competitors" }
{ "event": "lane_completed", "lane_id": "competitors", "claim_count": 7,
                             "no_evidence_found": false, "had_tool_failure": false }
{ "event": "awaiting_human", "awaiting": { /* Awaiting */ } }
{ "event": "run_completed",  "run_id": "..." }
{ "event": "error",          "detail": "..." }
```

**SSE is an optimisation, not the source of truth.** On any `event`, the client may
re-fetch `GET /runs/{id}`. Build the UI so it works correctly with polling alone —
then layer SSE on for liveness. A dropped connection must never corrupt UI state.

---

## Behaviour the UI has to handle

- **Intake loops.** Answering an `intake_question` frequently returns
  `awaiting_human` with *another* question. This is normal, not an error — Intake
  keeps asking until niche + audience + core question are concrete. There is no
  fixed number of turns.
- **Lane count is dynamic.** 2 lanes or 5, decided per-idea. Never hardcode three,
  never assume the reference names (Customer Pain / Competitors / Distribution).
  Always render off `lane_progress` — always drive lane UI from `name`, and use
  `archetype` only as a cosmetic hint. A run may be all `"other"`; that's valid and
  must look normal, not unstyled.
- **`no_evidence_found` is a success, not a failure.** Render it as a real result.
  It is visually distinct from `had_tool_failure`, which *is* a problem.
- **`rerun_lane_id`** sends the run backwards into `research`. Status returns to
  `running`. The UI must not assume the pipeline only moves forward.
- **Caveats are already inline** in `FindingGroup.points`. Never truncate or
  summarise them — Skeptic and Merge worked to preserve those hedges.
- **A "not enough evidence" verdict is a legitimate outcome.** Don't style it as an
  error state.
