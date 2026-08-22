# Workflow: Supervisor — Log and Monitor Every Agent

## Objective
Cross-cutting observability over the whole pipeline. The Supervisor does not sit in
the linear Intake → Plan → Research → Skeptic → Merge → Human Gate flow — it watches
all of it.

## Required Inputs
- Every agent's inputs and outputs, as they happen (not reconstructed after the fact).
- Timing for each stage.
- Any tool failures or retries reported by an agent.

## Steps
1. For every agent invocation, log: agent name, stage, input summary, output summary,
   timestamp, duration.
2. For every tool failure reported by an agent (see `03_research_lane.md` edge
   cases), log the failure and whether it was retried/recovered.
3. If a stage takes far longer than expected, or a Research lane comes back empty
   repeatedly, flag it — this may indicate a broken tool, not a genuinely empty
   result.
4. Persist logs somewhere durable (`logs/`), not just `.tmp/` — these are the audit
   trail for how a recommendation was produced, useful even after the run ends.
5. On request, summarize a full run: which lanes ran, what Skeptic killed, what
   Merge produced, what the human chose, and total cost/time.

## Tools
Not built yet. Expected: a structured logger writing to `logs/`, possibly a simple
run-summary tool that reads those logs back.

## Expected Output
Structured, append-only run logs in `logs/`, plus an on-demand run summary.

## Edge Cases
- **An agent fails silently (no error, but obviously wrong output — e.g. empty
  research with no failure reported)**: Supervisor should still flag this as
  suspicious based on shape of the output, not just rely on agents self-reporting
  failures.
- **Cost tracking matters** (paid API calls in Research/tools): Supervisor should
  track per-run cost where available, so repeated re-runs of an idea don't silently
  rack up spend.
