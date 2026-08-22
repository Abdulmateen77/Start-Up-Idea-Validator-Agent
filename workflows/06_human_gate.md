# Workflow: Human Gate — The Human Decides the Next Move

## Objective
Present the one-page recommendation and a short menu of next moves. Capture the
human's decision. The model does not pick the next move — the human does.

## Required Inputs
- One-page recommendation from Merge.

## Steps
1. Present the recommendation as-is — don't re-summarize it into something shorter
   and lose the caveats/gaps Skeptic and Merge preserved.
2. Offer a small set of concrete next-move options tailored to what's actually
   missing or uncertain in the recommendation (not a generic fixed menu every time).
   Reference example options: customer interviews, competitor teardown, a small
   calculator/model, or pass.
3. Record whichever option the human picks (or a custom next move they specify).
4. Hand the decision to Supervisor for logging. This ends the pipeline run.

## Tools
None yet. Whatever mechanism presents this to the human (FastAPI endpoint response,
CLI prompt, etc.) is an implementation detail decided when building starts.

## Expected Output
```
Recommendation: [as produced by Merge]
Next-move options offered: [...]
Human's decision: [chosen option or custom note]
```

## Edge Cases
- **Human wants to re-run a lane instead of picking a next move**: that's a valid
  outcome — route back to Plan/Research for that lane rather than forcing a choice
  from the fixed menu.
- **Human doesn't respond / gate times out**: Supervisor should log this as an
  incomplete run, not a "pass" decision.
