# Workflow: Skeptic — Attack the Evidence

## Objective
Adversarially review every claim from every research lane. Weak or unsupported
claims don't survive to Merge. Checking the evidence is this agent's entire job —
not a light pass at the end.

## Required Inputs
- All findings from all Research lane agents (claim + source pairs, including
  explicitly unsourced claims and "no evidence found" results).

## Steps
1. For each claim, ask:
   - Is the source credible and does it actually say what the claim says it says?
   - Is this a single data point being treated as a trend?
   - Does this claim contradict another claim from a different lane?
   - Is this claim actually relevant to the core question from Intake, or is it
     scope creep?
2. Classify each claim: **survives**, **killed** (with a one-line reason), or
   **survives with caveat** (weak but not worthless — flag the weakness explicitly
   so Merge doesn't overstate it).
3. Note any gap: a question from Plan that no lane actually answered with credible
   evidence. Gaps are useful output, not a reason to fabricate a claim to fill them.

## Tools
None yet. This is a reasoning/critique step over existing findings — no new external
calls expected. May later use a tool to re-verify a source URL is live/accurate.

## Expected Output
```
Survives:
  - "X charges $49/mo..." (source verified, pricing page checked)
Killed:
  - "Merchants love AI bookkeeping" — no source, single anecdote, contradicts
    Customer Pain lane's finding that most merchants haven't tried any AI tool
Gaps:
  - Distribution lane didn't find actual CAC/channel cost data, only channel names
```

## Edge Cases
- **Almost everything gets killed**: that's a valid, important outcome — report it
  plainly to Merge rather than softening it to make the pipeline look productive.
- **A claim is plausible but genuinely unverifiable given available tools**: mark it
  "survives with caveat," don't kill it just because verification is hard — but don't
  let Merge present it with unwarranted confidence either.
