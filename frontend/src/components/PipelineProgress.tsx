import React from "react";
import { LaneProgress, ResearchLane, Stage, Status } from "@/lib/types";
import { ArchetypeBadge } from "./ArchetypeIcon";
import {
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Search,
  Check,
  ShieldCheck,
  GitMerge,
  FileCheck2,
  Sparkles,
} from "lucide-react";

interface PipelineProgressProps {
  stage: Stage;
  status: Status;
  lanes: ResearchLane[];
  laneProgress: LaneProgress[];
}

export function PipelineProgress({
  stage,
  status,
  lanes,
  laneProgress,
}: PipelineProgressProps) {
  // If lanes exist, use laneProgress; if laneProgress is empty but lanes exist, construct default pending state
  const displayProgress: LaneProgress[] =
    laneProgress.length > 0
      ? laneProgress
      : lanes.map((l) => ({
          lane_id: l.lane_id,
          name: l.name,
          archetype: l.archetype,
          state: "pending",
          claim_count: 0,
          no_evidence_found: false,
          had_tool_failure: false,
        }));

  // Helper to get lane question if available
  const getLaneQuestion = (lane_id: string) => {
    return lanes.find((l) => l.lane_id === lane_id)?.question;
  };

  const completedLanesCount = displayProgress.filter(
    (l) => l.state === "done" || l.state === "failed"
  ).length;
  const totalLanes = displayProgress.length;

  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-5 shadow-lg backdrop-blur-sm space-y-6">
      {/* Header & Stage Track */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-blue-500/20 text-blue-400">
              <Search className="w-4 h-4" />
            </div>
            <h3 className="text-base font-semibold text-slate-100">
              Parallel Research & Evidence Extraction
            </h3>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {totalLanes > 0
              ? `${completedLanesCount} of ${totalLanes} independent research vectors evaluated`
              : "Decomposing brief into dynamic research lanes..."}
          </p>
        </div>

        {/* Global Pipeline Stage Indicator */}
        <div className="flex items-center gap-1.5 bg-slate-950/80 px-3 py-1.5 rounded-lg border border-slate-800 self-start sm:self-auto">
          <div className="text-xs font-medium text-slate-400">Current Phase:</div>
          <div className="text-xs font-semibold text-blue-300 capitalize flex items-center gap-1.5">
            {status === "running" && (
              <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />
            )}
            {stage === "intake" && "Intake Refinement"}
            {stage === "plan" && "Lane Decomposition"}
            {stage === "research" && "Parallel Scraping & Retrieval"}
            {stage === "skeptic" && "Adversarial Skeptic Review"}
            {stage === "merge" && "Evidence Synthesis"}
            {stage === "human_gate" && "Human Decision Gate"}
            {stage === "done" && "Pipeline Concluded"}
            {stage === "failed" && "Execution Halted"}
          </div>
        </div>
      </div>

      {/* Pipeline Stage Bar Visualizer */}
      <div className="grid grid-cols-2 sm:grid-cols-6 gap-2 text-xs font-medium">
        {[
          { key: "intake", label: "1. Intake", icon: Sparkles },
          { key: "plan", label: "2. Plan", icon: Search },
          { key: "research", label: "3. Research", icon: Search },
          { key: "skeptic", label: "4. Skeptic", icon: ShieldCheck },
          { key: "merge", label: "5. Merge", icon: GitMerge },
          { key: "human_gate", label: "6. Human Gate", icon: FileCheck2 },
        ].map((step, idx) => {
          const stagesOrder: Stage[] = [
            "intake",
            "plan",
            "research",
            "skeptic",
            "merge",
            "human_gate",
            "done",
          ];
          const currentIndex = stagesOrder.indexOf(stage);
          const stepIndex = stagesOrder.indexOf(step.key as Stage);
          const isDone = currentIndex > stepIndex || stage === "done";
          const isCurrent = stage === step.key;

          const StepIcon = step.icon;

          return (
            <div
              key={step.key}
              className={`p-2.5 rounded-lg border flex items-center gap-2 transition ${
                isCurrent
                  ? "bg-blue-950/60 border-blue-500/50 text-blue-200 ring-1 ring-blue-500/40"
                  : isDone
                  ? "bg-slate-900/90 border-slate-800 text-slate-300"
                  : "bg-slate-950/40 border-slate-800/40 text-slate-600"
              }`}
            >
              {isCurrent && status === "running" ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400 shrink-0" />
              ) : isDone ? (
                <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              ) : (
                <StepIcon className="w-3.5 h-3.5 opacity-50 shrink-0" />
              )}
              <span className="truncate">{step.label}</span>
            </div>
          );
        })}
      </div>

      {/* Dynamic Research Lanes Grid */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
            Active Research Sub-Agents ({totalLanes} Lanes)
          </span>
          <span className="text-xs text-slate-500">
            Parallel fan-out via LangGraph Send
          </span>
        </div>

        {displayProgress.length === 0 ? (
          <div className="p-8 text-center bg-slate-950/40 border border-slate-800 rounded-lg text-sm text-slate-500">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-2 text-slate-600" />
            Lanes will be dynamically generated once the idea brief is finalized.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {displayProgress.map((lane) => {
              const question = getLaneQuestion(lane.lane_id);
              const isRunning = lane.state === "running";
              const isDone = lane.state === "done";
              const isFailed = lane.state === "failed";
              const isPending = lane.state === "pending";

              return (
                <div
                  key={lane.lane_id}
                  className={`rounded-lg border p-4 transition flex flex-col justify-between ${
                    isRunning
                      ? "bg-blue-950/20 border-blue-500/40 shadow-md shadow-blue-950/20"
                      : isDone && lane.had_tool_failure
                      ? "bg-amber-950/20 border-amber-500/30"
                      : isDone && lane.no_evidence_found
                      ? "bg-slate-900 border-slate-700/80"
                      : isDone
                      ? "bg-slate-900/90 border-slate-800"
                      : isFailed
                      ? "bg-rose-950/20 border-rose-500/40"
                      : "bg-slate-950/50 border-slate-800/60 opacity-75"
                  }`}
                >
                  <div>
                    {/* Top: Archetype tag & Lane Status Pill */}
                    <div className="flex items-start justify-between gap-2 mb-2.5">
                      <ArchetypeBadge archetype={lane.archetype} />

                      {isRunning && (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-blue-400 bg-blue-950/80 border border-blue-500/40 px-2 py-0.5 rounded-full">
                          <Loader2 className="w-3 h-3 animate-spin" />
                          Gathering Evidence
                        </span>
                      )}

                      {isPending && (
                        <span className="inline-flex items-center gap-1 text-xs text-slate-500 bg-slate-900 border border-slate-800 px-2 py-0.5 rounded-full">
                          <Clock className="w-3 h-3" />
                          Queued
                        </span>
                      )}

                      {isDone && !lane.had_tool_failure && !lane.no_evidence_found && (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-400 bg-emerald-950/80 border border-emerald-500/40 px-2 py-0.5 rounded-full">
                          <CheckCircle2 className="w-3 h-3" />
                          Complete
                        </span>
                      )}

                      {isFailed && (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-400 bg-rose-950/80 border border-rose-500/40 px-2 py-0.5 rounded-full">
                          <AlertTriangle className="w-3 h-3" />
                          Lane Failed
                        </span>
                      )}
                    </div>

                    {/* Lane Name */}
                    <h4 className="text-sm font-semibold text-slate-100 mb-1.5">
                      {lane.name}
                    </h4>

                    {/* Lane Question */}
                    {question && (
                      <p className="text-xs text-slate-400 leading-relaxed mb-3">
                        {question}
                      </p>
                    )}
                  </div>

                  {/* Lane Results / Status Footer */}
                  <div className="pt-3 border-t border-slate-800/80 mt-2">
                    {/* Legitimate No Evidence Found State */}
                    {lane.no_evidence_found && (
                      <div className="flex items-center gap-2 p-2 rounded bg-slate-800/70 border border-slate-700 text-xs text-slate-300">
                        <FileCheck2 className="w-4 h-4 text-emerald-400 shrink-0" />
                        <div>
                          <span className="font-semibold text-slate-200">
                            Verified finding:
                          </span>{" "}
                          0 restrictive claims found (absence of barrier confirmed).
                        </div>
                      </div>
                    )}

                    {/* Tool Failure State */}
                    {lane.had_tool_failure && (
                      <div className="flex items-center gap-2 p-2 rounded bg-amber-950/50 border border-amber-500/40 text-xs text-amber-200">
                        <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                        <div>
                          <span className="font-semibold text-amber-300">
                            Tool Failure Notice:
                          </span>{" "}
                          Scraper/extraction error encountered on external source.
                        </div>
                      </div>
                    )}

                    {/* Standard Claims Count */}
                    {!lane.no_evidence_found && !lane.had_tool_failure && isDone && (
                      <div className="flex items-center justify-between text-xs text-slate-400">
                        <span>Extracted Claims:</span>
                        <span className="font-semibold text-slate-200 bg-slate-800 px-2 py-0.5 rounded">
                          {lane.claim_count} validated claims
                        </span>
                      </div>
                    )}

                    {isRunning && (
                      <div className="space-y-1.5">
                        <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                          <div className="h-full bg-blue-500 animate-pulse rounded-full w-2/3"></div>
                        </div>
                        <div className="flex justify-between text-[11px] text-slate-400">
                          <span>Scanning sources...</span>
                          <span>{lane.claim_count} claims drafted</span>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
