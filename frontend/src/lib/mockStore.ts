import { PRESET_SCENARIOS, createNewMockRun, toRunSummary } from "./mockData";
import {
  RunView,
  RunSummary,
  RespondRequest,
  SSEEvent,
  ResearchLane,
  LaneProgress,
  Recommendation,
  NextMove,
} from "./types";

// In-memory store of active runs
class MockStore {
  private runs: Map<string, RunView> = new Map();
  private subscribers: Map<string, Set<(event: SSEEvent) => void>> = new Map();

  constructor() {
    this.resetToPresets();
  }

  public resetToPresets(): void {
    this.runs.clear();
    Object.values(PRESET_SCENARIOS).forEach((run) => {
      // Clone deeply so mutations don't corrupt constants
      this.runs.set(run.run_id, JSON.parse(JSON.stringify(run)));
    });
  }

  public listRuns(): RunSummary[] {
    const list = Array.from(this.runs.values()).map(toRunSummary);
    return list.sort(
      (a, b) =>
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );
  }

  public getRun(id: string): RunView | null {
    const run = this.runs.get(id);
    if (!run) return null;
    return JSON.parse(JSON.stringify(run));
  }

  public createRun(raw_idea: string): RunView {
    const run = createNewMockRun(raw_idea);
    this.runs.set(run.run_id, run);
    this.notify(run.run_id, {
      event: "awaiting_human",
      awaiting: run.awaiting!,
    });
    return JSON.parse(JSON.stringify(run));
  }

  public respond(run_id: string, request: RespondRequest): RunView {
    const run = this.runs.get(run_id);
    if (!run) {
      throw new Error("run not found");
    }

    if (run.status !== "awaiting_human") {
      throw new Error("run is not awaiting human input");
    }

    if (request.kind === "intake_answer") {
      if (run.awaiting?.kind !== "intake_question") {
        throw new Error("wrong kind for the current pause");
      }

      const turnIndex = run.awaiting.turn_index;
      run.intake_turns.push({
        role: "human",
        content: request.message,
      });
      run.updated_at = new Date().toISOString();

      if (turnIndex === 1) {
        // Multi-turn intake loop: ask question 2
        const nextQ = `What is the primary operational friction or bottleneck that ${request.message.trim()} experiences?`;
        run.intake_turns.push({
          role: "agent",
          content: nextQ,
        });
        run.awaiting = {
          kind: "intake_question",
          question: nextQ,
          turn_index: 2,
        };
        this.notify(run_id, {
          event: "awaiting_human",
          awaiting: run.awaiting,
        });
      } else if (turnIndex === 2) {
        // Multi-turn intake loop: ask question 3
        const nextQ =
          "What is the single most critical assumption or core question we must validate with hard evidence before building?";
        run.intake_turns.push({
          role: "agent",
          content: nextQ,
        });
        run.awaiting = {
          kind: "intake_question",
          question: nextQ,
          turn_index: 3,
        };
        this.notify(run_id, {
          event: "awaiting_human",
          awaiting: run.awaiting,
        });
      } else {
        // Intake complete! Transition to plan -> research
        run.status = "running";
        run.stage = "plan";
        run.awaiting = null;
        run.brief = {
          niche: `${run.raw_idea.slice(0, 45)}... validation niche`,
          audience:
            run.intake_turns.find((t) => t.role === "human")?.content ||
            "Target operators",
          core_question: request.message,
        };
        this.notify(run_id, { event: "stage_changed", stage: "plan" });

        // Trigger asynchronous pipeline progression
        this.simulatePipelineProgression(run_id);
      }

      return JSON.parse(JSON.stringify(run));
    }

    if (request.kind === "gate_decision") {
      if (run.awaiting?.kind !== "gate_decision") {
        throw new Error("wrong kind for the current pause");
      }

      if ("rerun_lane_id" in request && request.rerun_lane_id) {
        // BACKWARDS FLOW: rerun specified lane
        const laneId = request.rerun_lane_id;
        run.status = "running";
        run.stage = "research";
        run.awaiting = null;
        run.human_decision = {
          chosen_move_id: null,
          custom_note: null,
          rerun_lane_id: laneId,
        };
        run.updated_at = new Date().toISOString();

        // Mark target lane as running
        const targetLane = run.lane_progress.find((l) => l.lane_id === laneId);
        if (targetLane) {
          targetLane.state = "running";
          targetLane.claim_count = 0;
          targetLane.no_evidence_found = false;
          targetLane.had_tool_failure = false;
        }

        this.notify(run_id, { event: "stage_changed", stage: "research" });
        this.notify(run_id, {
          event: "lane_started",
          lane_id: laneId,
          name: targetLane?.name || laneId,
        });

        // Trigger simulation back through skeptic -> merge -> gate
        this.simulateLaneRerunProgression(run_id, laneId);
        return JSON.parse(JSON.stringify(run));
      }

      // Finish run with human decision
      run.status = "done";
      run.stage = "done";
      run.awaiting = null;
      run.updated_at = new Date().toISOString();
      run.human_decision = {
        chosen_move_id: "chosen_move_id" in request ? request.chosen_move_id : null,
        custom_note: "custom_note" in request ? request.custom_note : null,
        rerun_lane_id: null,
      };

      this.notify(run_id, { event: "stage_changed", stage: "done" });
      this.notify(run_id, { event: "run_completed", run_id });
      return JSON.parse(JSON.stringify(run));
    }

    throw new Error("invalid respond payload");
  }

  public subscribe(
    run_id: string,
    callback: (event: SSEEvent) => void
  ): () => void {
    if (!this.subscribers.has(run_id)) {
      this.subscribers.set(run_id, new Set());
    }
    this.subscribers.get(run_id)!.add(callback);

    return () => {
      const set = this.subscribers.get(run_id);
      if (set) {
        set.delete(callback);
      }
    };
  }

  private notify(run_id: string, event: SSEEvent): void {
    const set = this.subscribers.get(run_id);
    if (set) {
      set.forEach((cb) => {
        try {
          cb(event);
        } catch {
          // ignore callback error
        }
      });
    }
  }

  private simulatePipelineProgression(run_id: string): void {
    setTimeout(() => {
      const run = this.runs.get(run_id);
      if (!run || run.status !== "running") return;

      // Plan stage generates lanes
      const generatedLanes: ResearchLane[] = [
        {
          lane_id: "lane-pain",
          name: "Customer Pain & Urgency Verification",
          question:
            "Do target customers actively experience acute pain and seek workarounds?",
          archetype: "customer_pain",
        },
        {
          lane_id: "lane-comp",
          name: "Direct Competitor & Substitute Analysis",
          question:
            "What existing incumbents or manual workflows do they currently use?",
          archetype: "competitors",
        },
        {
          lane_id: "lane-dist",
          name: "Go-to-Market Distribution Feasibility",
          question:
            "Are there accessible, cost-effective distribution channels to reach buyers?",
          archetype: "distribution",
        },
      ];

      const initialProgress: LaneProgress[] = generatedLanes.map((l) => ({
        lane_id: l.lane_id,
        name: l.name,
        archetype: l.archetype,
        state: "running",
        claim_count: 0,
        no_evidence_found: false,
        had_tool_failure: false,
      }));

      run.stage = "research";
      run.lanes = generatedLanes;
      run.lane_progress = initialProgress;
      run.updated_at = new Date().toISOString();

      this.notify(run_id, { event: "stage_changed", stage: "research" });
      generatedLanes.forEach((l) => {
        this.notify(run_id, {
          event: "lane_started",
          lane_id: l.lane_id,
          name: l.name,
        });
      });

      // Simulate parallel research lanes completing
      setTimeout(() => {
        const r2 = this.runs.get(run_id);
        if (!r2 || r2.status !== "running") return;

        const lp0 = r2.lane_progress[0];
        if (lp0) {
          lp0.state = "done";
          lp0.claim_count = 5;
          this.notify(run_id, {
            event: "lane_completed",
            lane_id: lp0.lane_id,
            claim_count: 5,
            no_evidence_found: false,
            had_tool_failure: false,
          });
        }
      }, 1500);

      setTimeout(() => {
        const r3 = this.runs.get(run_id);
        if (!r3 || r3.status !== "running") return;

        const lp1 = r3.lane_progress[1];
        if (lp1) {
          lp1.state = "done";
          lp1.claim_count = 4;
          this.notify(run_id, {
            event: "lane_completed",
            lane_id: lp1.lane_id,
            claim_count: 4,
            no_evidence_found: false,
            had_tool_failure: false,
          });
        }
      }, 2800);

      setTimeout(() => {
        const r4 = this.runs.get(run_id);
        if (!r4 || r4.status !== "running") return;

        const lp2 = r4.lane_progress[2];
        if (lp2) {
          lp2.state = "done";
          lp2.claim_count = 3;
          this.notify(run_id, {
            event: "lane_completed",
            lane_id: lp2.lane_id,
            claim_count: 3,
            no_evidence_found: false,
            had_tool_failure: false,
          });
        }

        // Move to skeptic
        r4.stage = "skeptic";
        r4.updated_at = new Date().toISOString();
        this.notify(run_id, { event: "stage_changed", stage: "skeptic" });

        // Move to merge
        setTimeout(() => {
          const r5 = this.runs.get(run_id);
          if (!r5 || r5.status !== "running") return;

          r5.stage = "merge";
          r5.updated_at = new Date().toISOString();
          this.notify(run_id, { event: "stage_changed", stage: "merge" });

          // Move to human_gate
          setTimeout(() => {
            const r6 = this.runs.get(run_id);
            if (!r6 || r6.status !== "running") return;

            const rec: Recommendation = {
              core_question:
                r6.brief?.core_question ||
                `Validation analysis for ${r6.raw_idea}`,
              findings: [
                {
                  lane_name: "Customer Pain & Urgency Verification",
                  points: [
                    "Target operators report recurring manual friction, spending 10-15 hours weekly on ad-hoc spreadsheets.",
                    "High willingness to adopt specialized automated tools if setup time is under 1 hour.",
                    "Caveat: Budget authority requires department head sign-off for software contracts over $500/mo.",
                  ],
                },
                {
                  lane_name: "Direct Competitor & Substitute Analysis",
                  points: [
                    "Legacy desktop suites dominate older firms but lack modern web integrations and real-time collaboration.",
                    "2 emerging seed-stage startups launched comparable tooling in Q3, focusing primarily on enterprise accounts.",
                  ],
                },
                {
                  lane_name: "Go-to-Market Distribution Feasibility",
                  points: [
                    "Strong organic search demand on high-intent long-tail keywords with low keyword difficulty (<25).",
                    "Industry Slack/Discord communities and niche trade directories provide direct outbound reach.",
                  ],
                },
              ],
              gaps: [
                "Pricing elasticity between freemium vs upfront subscription has not been quantitatively benchmarked.",
                "Data security and export compliance constraints for regulated enterprise accounts require further scrutiny.",
              ],
              verdict:
                "Proceed to customer interviews: validated niche urgency and accessible distribution wedge with manageable competitive pressure.",
            };

            const nextMoves: NextMove[] = [
              {
                move_id: "customer_interviews",
                label: "Conduct 5 Customer Discovery Calls",
                rationale:
                  "Schedule 30-min discovery interviews with 5 active operators to validate willingness to pay $199/mo.",
              },
              {
                move_id: "landing_page_smoke_test",
                label: "Deploy Waitlist Smoke Test",
                rationale:
                  "Launch a focused landing page with interactive demo video to gauge email signup conversion rate.",
              },
              {
                move_id: "competitor_teardown",
                label: "Detailed Competitor Pricing Teardown",
                rationale:
                  "Map feature tiers and hidden fees of existing solutions to construct optimal pricing packaging.",
              },
              {
                move_id: "pass_pivot",
                label: "Pass on this Thesis",
                rationale:
                  "Archive this idea if CAC or competitive resistance is deemed outside target risk tolerance.",
              },
            ];

            r6.stage = "human_gate";
            r6.status = "awaiting_human";
            r6.recommendation = rec;
            r6.awaiting = {
              kind: "gate_decision",
              recommendation: rec,
              next_moves: nextMoves,
            };
            r6.updated_at = new Date().toISOString();

            this.notify(run_id, {
              event: "awaiting_human",
              awaiting: r6.awaiting,
            });
          }, 1500);
        }, 1200);
      }, 4000);
    }, 1200);
  }

  private simulateLaneRerunProgression(run_id: string, laneId: string): void {
    setTimeout(() => {
      const run = this.runs.get(run_id);
      if (!run || run.status !== "running") return;

      const target = run.lane_progress.find((l) => l.lane_id === laneId);
      if (target) {
        target.state = "done";
        target.claim_count = Math.floor(Math.random() * 5) + 3;
        this.notify(run_id, {
          event: "lane_completed",
          lane_id: target.lane_id,
          claim_count: target.claim_count,
          no_evidence_found: false,
          had_tool_failure: false,
        });
      }

      run.stage = "skeptic";
      run.updated_at = new Date().toISOString();
      this.notify(run_id, { event: "stage_changed", stage: "skeptic" });

      setTimeout(() => {
        const r2 = this.runs.get(run_id);
        if (!r2 || r2.status !== "running") return;

        r2.stage = "merge";
        r2.updated_at = new Date().toISOString();
        this.notify(run_id, { event: "stage_changed", stage: "merge" });

        setTimeout(() => {
          const r3 = this.runs.get(run_id);
          if (!r3 || r3.status !== "running") return;

          r3.stage = "human_gate";
          r3.status = "awaiting_human";
          if (r3.recommendation) {
            r3.awaiting = {
              kind: "gate_decision",
              recommendation: r3.recommendation,
              next_moves: [
                {
                  move_id: "customer_interviews",
                  label: "Proceed with 5 Customer Discovery Calls",
                  rationale: `Updated analysis for ${target?.name || laneId} reinforces high buyer pain.`,
                },
                {
                  move_id: "smoke_test",
                  label: "Launch Waitlist Smoke Test",
                  rationale: "Drive 100 targeted visitors to validate conversion threshold.",
                },
                {
                  move_id: "pass",
                  label: "Pass on this Idea",
                  rationale: "Archive if remaining uncertainties are too severe.",
                },
              ],
            };
          }
          r3.updated_at = new Date().toISOString();

          this.notify(run_id, {
            event: "awaiting_human",
            awaiting: r3.awaiting!,
          });
        }, 1200);
      }, 1000);
    }, 2000);
  }
}

// Global singleton for mock server routes
export const mockStore = new MockStore();
