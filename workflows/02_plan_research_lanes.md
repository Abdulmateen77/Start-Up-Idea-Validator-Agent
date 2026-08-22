# Workflow: Plan — Turn the Brief into Research Lanes

## Objective
Decompose the refined idea brief into a small set of parallel research lanes, each
with its own concrete question. This is what turns "one question" into a graph.

## Required Inputs
- Refined idea brief from Intake (niche, audience, core question).

## Steps
1. Read the brief. Decide which lanes are actually relevant to *this* idea — lanes
   are not fixed. Common lanes (from the reference example) include:
   - **Customer Pain** — how does the target audience handle this problem today?
   - **Competitors** — who already sells something like this, and how do they price it?
   - **Distribution** — how would you actually reach this audience?
   Other ideas may need different or additional lanes (e.g. Regulatory, Technical
   Feasibility, Unit Economics) — don't force-fit the default three if they don't fit.
2. For each lane, write one specific, answerable question (not a restatement of the
   core question).
3. Hand off each lane + its question to a Research agent instance. Lanes run in
   parallel — no lane should depend on another lane's output.

## Tools
None yet. This is a decomposition/reasoning step. No external calls expected.

## Expected Output
A list of lanes, each with a name and a specific question, e.g.:
```
- Customer Pain: How do Shopify merchants in this revenue band handle bookkeeping today?
- Competitors: Who already sells bookkeeping tools/services to this segment, and how do they price?
- Distribution: What channels would actually reach solo-operator Shopify merchants?
```

## Edge Cases
- **Idea doesn't cleanly split into lanes**: it's fine to have 2 lanes or 5 — don't
  force a fixed count.
- **A lane's question turns out to depend on another lane's answer**: that's a sign
  the lanes weren't independent — merge them or resequence, don't fan them out in
  parallel with a hidden dependency.
