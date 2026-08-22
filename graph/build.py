"""
Graph wiring. OWNERSHIP: Lead only.

    INTAKE ⇄ INTAKE_WAIT  →  PLAN  ⇉ RESEARCH ×N ⇉  SKEPTIC → MERGE → GATE ⇄ GATE_WAIT
      (loop until brief)        (Send fan-out)      (fan-in)              (→ END or back
                                                                            to RESEARCH)

Two structural decisions worth understanding before changing anything here.

**Why each human-in-the-loop stage is TWO nodes.** LangGraph re-executes a node from
the top when it resumes from `interrupt()` — `interrupt()` raises the first time and
returns the resume value the second. Anything before the interrupt therefore runs
twice. If a node both called the LLM and interrupted, every human answer would cost a
duplicate Gemini call. So the LLM work lives in `intake` / `human_gate`, and the
interrupt lives alone in a cheap `*_wait` node that is safe to re-run.

**Why nodes are injected.** `NodeRegistry` lets the graph be built with fakes, so the
fan-out, the fan-in reducer, and both interrupt loops can be tested before Hermes and
Antigravity deliver their nodes. Integration bugs surface here, not at merge.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt

from graph.state import HumanDecision, IntakeTurn, LaneTask, RunState, Stage

NodeFn = Callable[[Any], dict]


@dataclass(frozen=True, slots=True)
class NodeRegistry:
    """The six pipeline nodes. Swap any of them for a fake in tests."""

    intake: NodeFn
    plan: NodeFn
    research: NodeFn
    skeptic: NodeFn
    merge: NodeFn
    human_gate: NodeFn


def default_registry() -> NodeRegistry:
    """
    The real nodes. Imported lazily and individually so that a session which hasn't
    delivered yet produces a clear ImportError naming its own module, rather than
    breaking `import graph.build` for everyone.
    """
    from agents.human_gate import human_gate_node
    from agents.intake import intake_node
    from agents.merge import merge_node
    from agents.planner import plan_node
    from agents.research import research_node
    from agents.skeptic import skeptic_node

    return NodeRegistry(
        intake=intake_node,
        plan=plan_node,
        research=research_node,
        skeptic=skeptic_node,
        merge=merge_node,
        human_gate=human_gate_node,
    )


# ---------------------------------------------------------------------------
# Interrupt nodes — no LLM calls, cheap to re-execute on resume
# ---------------------------------------------------------------------------


def intake_wait_node(state: RunState) -> dict:
    """
    Block until the human answers Intake's latest question.

    The question is already the last agent turn — `intake` put it there — so this
    node does no reasoning of its own and is safe to re-run on resume.
    """
    turns = state.get("intake_turns") or []
    question = next(
        (t.content for t in reversed(turns) if t.role == "agent"),
        "Tell me more about your idea.",
    )

    answer = interrupt({"kind": "intake_question", "question": question})

    text = answer if isinstance(answer, str) else str(answer)
    return {"intake_turns": [*turns, IntakeTurn(role="human", content=text)]}


def human_gate_wait_node(state: RunState) -> dict:
    """Block until the human picks a next move. `human_gate` built the menu."""
    decision = interrupt(
        {
            "kind": "gate_decision",
            "recommendation": state.get("recommendation"),
            "next_moves": state.get("next_moves") or [],
        }
    )

    if isinstance(decision, HumanDecision):
        parsed = decision
    elif isinstance(decision, dict):
        parsed = HumanDecision(**decision)
    else:
        parsed = HumanDecision(custom_note=str(decision))

    # A re-run keeps the run alive; anything else ends it.
    stage = Stage.RESEARCH if parsed.rerun_lane_id else Stage.DONE
    return {"human_decision": parsed, "stage": stage}


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def _route_after_intake(state: RunState) -> str:
    """Loop back for another question until Intake has produced a brief."""
    return "plan" if state.get("brief") else "intake_wait"


def _fan_out_lanes(state: RunState) -> list[Send]:
    """
    Plan → Research. One `Send` per lane, dispatched concurrently.

    Each Research node receives a LaneTask, NOT the full RunState — see
    docs/ARCHITECTURE.md. Results fan back in through the `merge_findings` reducer.
    """
    return _sends_for(state, state.get("lanes") or [])


def _route_after_gate(state: RunState) -> list[Send] | str:
    """
    The pipeline is not forward-only: the human may send one lane back to Research.

    The `findings` reducer replaces by lane_id, so the re-run supersedes the stale
    result instead of leaving Skeptic to judge both.
    """
    decision = state.get("human_decision")
    if decision and decision.rerun_lane_id:
        lanes = [
            lane
            for lane in (state.get("lanes") or [])
            if lane.lane_id == decision.rerun_lane_id
        ]
        if lanes:
            return _sends_for(state, lanes)
    return END


def _sends_for(state: RunState, lanes: Iterable) -> list[Send]:
    brief = state.get("brief")
    run_id = state.get("run_id", "")
    return [
        Send(
            "research",
            LaneTask(run_id=run_id, lane=lane, brief=brief),
        )
        for lane in lanes
    ]


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

DEFAULT_DB = os.getenv("IVA_DB", "iva.sqlite")


def build_graph(registry: NodeRegistry | None = None, checkpointer: Any | None = None):
    """
    Compile the pipeline.

    A checkpointer is REQUIRED for interrupts to survive a process restart — a run
    can sit paused on a human for days. Pass one explicitly, or use
    `open_checkpointer()`.
    """
    nodes = registry or default_registry()

    b = StateGraph(RunState)

    b.add_node("intake", nodes.intake)
    b.add_node("intake_wait", intake_wait_node)
    b.add_node("plan", nodes.plan)
    b.add_node("research", nodes.research)
    b.add_node("skeptic", nodes.skeptic)
    b.add_node("merge", nodes.merge)
    b.add_node("human_gate", nodes.human_gate)
    b.add_node("human_gate_wait", human_gate_wait_node)

    b.add_edge(START, "intake")
    b.add_conditional_edges("intake", _route_after_intake, ["intake_wait", "plan"])
    b.add_edge("intake_wait", "intake")

    b.add_conditional_edges("plan", _fan_out_lanes, ["research"])
    b.add_edge("research", "skeptic")
    b.add_edge("skeptic", "merge")
    b.add_edge("merge", "human_gate")
    b.add_edge("human_gate", "human_gate_wait")
    b.add_conditional_edges("human_gate_wait", _route_after_gate, ["research", END])

    return b.compile(checkpointer=checkpointer)


def open_checkpointer(db_path: str | None = None):
    """
    Open the SQLite checkpointer as a context manager.

        with open_checkpointer() as cp:
            app = build_graph(checkpointer=cp)
    """
    from langgraph.checkpoint.sqlite import SqliteSaver

    return SqliteSaver.from_conn_string(db_path or DEFAULT_DB)
