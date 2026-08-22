// Frozen types matching docs/API_CONTRACT.md exactly

export type Stage =
  | "intake"
  | "plan"
  | "research"
  | "skeptic"
  | "merge"
  | "human_gate"
  | "done"
  | "failed";

export type Status = "running" | "awaiting_human" | "done" | "failed";

export interface IdeaBrief {
  niche: string;
  audience: string;
  core_question: string;
}

// Selects the backend research playbook. Useful in the UI for an icon or a subtle
// label — NEVER for layout logic. Treat it as a cosmetic hint with an open set:
// always handle "other", and never assume which archetypes a run will contain.
export type LaneArchetype =
  | "customer_pain"
  | "competitors"
  | "distribution"
  | "regulatory"
  | "unit_economics"
  | "technical_feasibility"
  | "other";

export interface ResearchLane {
  lane_id: string;
  name: string;
  question: string;
  archetype: LaneArchetype;
}

// Per-lane progress for the parallel fan-out. One entry per lane, live-updated.
export interface LaneProgress {
  lane_id: string;
  name: string;
  archetype: LaneArchetype;
  state: "pending" | "running" | "done" | "failed";
  claim_count: number;
  no_evidence_found: boolean;
  had_tool_failure: boolean;
}

export interface FindingGroup {
  lane_name: string;
  points: string[];
}

export interface Recommendation {
  core_question: string;
  findings: FindingGroup[];
  gaps: string[];
  verdict: string;
}

export interface NextMove {
  move_id: string;
  label: string;
  rationale: string;
}

export interface IntakeTurn {
  role: "agent" | "human";
  content: string;
}

export interface HumanDecision {
  chosen_move_id: string | null;
  custom_note: string | null;
  rerun_lane_id: string | null;
}

// Discriminated union — switch on `kind` to pick the UI.
export type Awaiting =
  | { kind: "intake_question"; question: string; turn_index: number }
  | { kind: "gate_decision"; recommendation: Recommendation; next_moves: NextMove[] };

export interface RunView {
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

export interface RunSummary {          // dashboard list item
  run_id: string;
  status: Status;
  stage: Stage;
  raw_idea: string;
  created_at: string;
  updated_at: string;
}

// Request and Response payloads from docs/API_CONTRACT.md
export interface CreateRunRequest {
  raw_idea: string;
}

export type IntakeAnswerResponse = {
  kind: "intake_answer";
  message: string;
};

export type GateDecisionMoveResponse = {
  kind: "gate_decision";
  chosen_move_id: string;
};

export type GateDecisionNoteResponse = {
  kind: "gate_decision";
  custom_note: string;
};

export type GateDecisionRerunResponse = {
  kind: "gate_decision";
  rerun_lane_id: string;
};

export type RespondRequest =
  | IntakeAnswerResponse
  | GateDecisionMoveResponse
  | GateDecisionNoteResponse
  | GateDecisionRerunResponse;

export interface ListRunsResponse {
  runs: RunSummary[];
}

export type SSEEvent =
  | { event: "stage_changed"; stage: Stage }
  | { event: "lane_started"; lane_id: string; name: string }
  | {
      event: "lane_completed";
      lane_id: string;
      claim_count: number;
      no_evidence_found: boolean;
      had_tool_failure: boolean;
    }
  | { event: "awaiting_human"; awaiting: Awaiting }
  | { event: "run_completed"; run_id: string }
  | { event: "error"; detail: string };
