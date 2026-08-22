# Workflow: Intake — Refine a Vague Idea

## Objective
Turn a vague, one-line idea into a detailed, comprehensive brief by pinning down a
specific **niche** and **target audience**, before any research starts. This agent's
job is to ask good follow-up questions, not to guess or pad a vague idea with
generic assumptions.

## Required Inputs
- Raw idea from the human (may be as short as one sentence, e.g. "Should we build AI
  bookkeeping for Shopify?").

## Steps
1. Read the raw idea. Identify what's missing to make it researchable:
   - Who exactly is the audience? (role, company size/stage, not just "small businesses")
   - What specific pain point or job-to-be-done is being targeted?
   - What's the smallest concrete version of this idea worth validating?
2. Ask the human targeted follow-up questions — one round at a time, not a giant
   questionnaire. Stop asking once niche + audience + core question are concrete.
3. Do not proceed to Plan until the brief has:
   - A specific niche (not "the market", not "businesses")
   - A specific target audience
   - A single core question the rest of the pipeline will investigate
4. Write the refined brief.

## Tools
None yet — this stage is pure conversation with the human. No external tool calls
expected. (Revisit if the human wants to attach reference docs/links for context —
would need a fetch/read tool at that point.)

## Expected Output
A short structured brief, e.g.:
```
Niche: AI bookkeeping for Shopify merchants doing $10k-100k/mo revenue
Audience: solo-operator merchants who currently do their own books or use a generic tool
Core question: Should we build AI bookkeeping for this segment of Shopify merchants?
```

## Edge Cases
- **Human gives an already-detailed idea**: skip back-and-forth, confirm the brief
  back to them in one message, move on.
- **Human is vague even after follow-ups**: don't force a niche — surface 2-3
  candidate niches/audiences and let the human pick, rather than inventing one.
- **Idea is not really an "idea" (e.g. a feature request, a research question with no
  build decision behind it)**: flag this back to the human before proceeding — the
  rest of the pipeline assumes a build/no-build decision at the end.
