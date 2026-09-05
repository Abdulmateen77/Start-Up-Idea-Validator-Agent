"""
Prompt text for the Merge node. Kept separate from wiring in agents/merge.py so
prompt iteration doesn't churn the node logic.
"""
from __future__ import annotations

MERGE_SYSTEM_INSTRUCTION = (
    "You synthesize surviving evidence into a single one-page recommendation, "
    "readable in under a minute. You never manufacture confidence the evidence "
    "doesn't support."
)


def build_merge_prompt(
    *,
    core_question: str,
    niche: str,
    audience: str,
    surviving_claims_block: str,
    gaps_block: str,
) -> str:
    """
    Builds the synthesis prompt. Only survivors (SURVIVES / SURVIVES_WITH_CAVEAT) are
    ever passed in `surviving_claims_block` — Merge must not see killed claims at all,
    so it structurally cannot leak one back into the recommendation.
    """
    return f"""
IDEA UNDER REVIEW
Niche: {niche}
Audience: {audience}
Core question: {core_question}

SURVIVING CLAIMS BY LANE (killed claims have already been removed — these are the
only claims you may draw on)
{surviving_claims_block}

GAPS FLAGGED BY THE SKEPTIC (questions no lane answered credibly)
{gaps_block}

TASK
Produce a one-page recommendation:
1. Set `core_question` to the exact core question restated above.
2. Group surviving claims into `findings`, one FindingGroup per lane, leading with
   whichever lane's points bear most directly on the core question. Each point in
   `points` must be a surviving claim's substance; if that claim carried a caveat,
   keep the caveat visible IN the point text itself (e.g. "... (caveat: single
   source, unverified)") — never drop a caveat for brevity.
3. Carry the gaps listed above straight into `gaps`, unchanged in substance.
4. Write `verdict` as plain prose: what the surviving evidence supports, what it
   doesn't, and where the real uncertainty is. If evidence points in different
   directions across lanes (e.g. strong pain but crowded competition), say so
   explicitly rather than averaging it into a mushy middle. Never manufacture
   confidence the evidence doesn't support — "not enough evidence yet, here's what's
   missing" is a legitimate verdict when that's what the record shows.
5. Do not include a next-move menu or recommend specific next actions beyond what
   belongs in the verdict text — that selection is a separate stage's job.
"""
