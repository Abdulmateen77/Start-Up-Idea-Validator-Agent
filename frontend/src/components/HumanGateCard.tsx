"use client";

import React, { useState } from "react";
import {
  Recommendation,
  NextMove,
  HumanDecision,
  ResearchLane,
  RespondRequest,
} from "@/lib/types";
import {
  Award,
  AlertCircle,
  RotateCcw,
  CheckCircle2,
  Send,
  Loader2,
  ArrowRight,
  FileQuestion,
  Lightbulb,
  HelpCircle,
} from "lucide-react";

interface HumanGateCardProps {
  recommendation: Recommendation;
  nextMoves: NextMove[];
  decision: HumanDecision | null;
  lanes: ResearchLane[];
  isAwaiting: boolean;
  onRespond: (payload: RespondRequest) => Promise<void>;
  isLoading?: boolean;
}

export function HumanGateCard({
  recommendation,
  nextMoves,
  decision,
  lanes,
  isAwaiting,
  onRespond,
  isLoading = false,
}: HumanGateCardProps) {
  const [selectedMoveId, setSelectedMoveId] = useState<string | null>(null);
  const [customNote, setCustomNote] = useState("");
  const [selectedRerunLane, setSelectedRerunLane] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"moves" | "custom" | "rerun">(
    "moves"
  );
  const [submitting, setSubmitting] = useState(false);

  const isBusy = isLoading || submitting;

  const isNotEnoughEvidenceVerdict =
    recommendation.verdict
      .toLowerCase()
      .includes("not enough evidence") ||
    recommendation.verdict.toLowerCase().includes("insufficient");

  const handleChooseMove = async (moveId: string) => {
    if (!isAwaiting || isBusy) return;
    setSubmitting(true);
    try {
      await onRespond({
        kind: "gate_decision",
        chosen_move_id: moveId,
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleCustomNoteSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAwaiting || isBusy || !customNote.trim()) return;
    setSubmitting(true);
    try {
      await onRespond({
        kind: "gate_decision",
        custom_note: customNote.trim(),
      });
    } finally {
      setSubmitting(false);
    }
  };

  const handleRerunSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isAwaiting || isBusy || !selectedRerunLane) return;
    setSubmitting(true);
    try {
      await onRespond({
        kind: "gate_decision",
        rerun_lane_id: selectedRerunLane,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rounded-2xl border-2 border-amber-500/40 bg-gradient-to-b from-slate-900 via-slate-900 to-slate-950 p-6 md:p-8 shadow-2xl shadow-amber-950/20 space-y-8">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-amber-500/20">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-400">
            <Award className="w-6 h-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold uppercase tracking-widest text-amber-400">
                Human Gate Decision
              </span>
              {isAwaiting ? (
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse">
                  Decision Required
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  Decision Recorded
                </span>
              )}
            </div>
            <h2 className="text-xl md:text-2xl font-bold text-slate-100 mt-1">
              One-Page Evidence Recommendation
            </h2>
          </div>
        </div>

        <div className="text-xs text-slate-400 bg-slate-950/80 px-3.5 py-2 rounded-lg border border-slate-800 self-start sm:self-auto">
          Synthesized from Skeptic-filtered research lanes
        </div>
      </div>

      {/* Core Question Highlight */}
      <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-5">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">
          <HelpCircle className="w-4 h-4 text-blue-400" />
          <span>Core Hypothesis Validated</span>
        </div>
        <p className="text-base md:text-lg font-semibold text-slate-100">
          {recommendation.core_question}
        </p>
      </div>

      {/* Verdict Card */}
      <div
        className={`rounded-xl p-5 border ${
          isNotEnoughEvidenceVerdict
            ? "bg-indigo-950/30 border-indigo-500/40"
            : "bg-emerald-950/30 border-emerald-500/40"
        }`}
      >
        <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider mb-2">
          {isNotEnoughEvidenceVerdict ? (
            <span className="text-indigo-300 flex items-center gap-1.5">
              <Lightbulb className="w-4 h-4 text-indigo-400" />
              Synthesis Verdict (Data Inconclusive / Pre-Maturity)
            </span>
          ) : (
            <span className="text-emerald-300 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Synthesis Verdict
            </span>
          )}
        </div>
        <p className="text-base font-medium leading-relaxed text-slate-100">
          {recommendation.verdict}
        </p>
      </div>

      {/* Detailed Findings Grouped by Lane */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
            Validated Evidence Findings
          </h3>
          <span className="text-xs text-slate-500">
            All points and inline caveats preserved in full
          </span>
        </div>

        <div className="grid grid-cols-1 gap-4">
          {recommendation.findings.map((group, gIdx) => (
            <div
              key={gIdx}
              className="bg-slate-950/60 border border-slate-800 rounded-xl p-5 space-y-3"
            >
              <h4 className="text-sm font-semibold text-blue-300 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                {group.lane_name}
              </h4>
              <ul className="space-y-2.5">
                {group.points.map((point, pIdx) => {
                  const isCaveat = point.toLowerCase().startsWith("caveat");
                  return (
                    <li
                      key={pIdx}
                      className={`text-sm leading-relaxed rounded-lg p-3 ${
                        isCaveat
                          ? "bg-amber-950/30 border border-amber-500/20 text-amber-200"
                          : "bg-slate-900/80 border border-slate-800/80 text-slate-200"
                      }`}
                    >
                      <div className="flex items-start gap-2.5">
                        <span className="text-slate-500 select-none mt-0.5">
                          •
                        </span>
                        <div className="flex-1 whitespace-pre-wrap">{point}</div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* Gaps / What is Missing (Prominently Rendered) */}
      <div className="bg-rose-950/20 border border-rose-500/30 rounded-xl p-5 space-y-3">
        <div className="flex items-center gap-2 text-rose-300">
          <AlertCircle className="w-4 h-4" />
          <h3 className="text-sm font-bold uppercase tracking-wider">
            Critical Uncertainties & Missing Evidence Gaps
          </h3>
        </div>
        <p className="text-xs text-slate-400">
          These gaps represent unverified assumptions or data voids that demand
          careful consideration:
        </p>
        <ul className="space-y-2">
          {recommendation.gaps.map((gap, idx) => (
            <li
              key={idx}
              className="text-sm text-rose-100 bg-rose-950/40 border border-rose-500/20 rounded-lg p-3 flex items-start gap-2.5"
            >
              <FileQuestion className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <span className="leading-relaxed">{gap}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Decision Section */}
      <div className="pt-6 border-t border-slate-800">
        {decision ? (
          <div className="bg-emerald-950/40 border border-emerald-500/30 rounded-xl p-5 space-y-2">
            <div className="flex items-center gap-2 text-emerald-300 text-sm font-semibold">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Human Decision Locked
            </div>
            {decision.chosen_move_id && (
              <p className="text-sm text-slate-200">
                <span className="text-slate-400">Chosen Move:</span>{" "}
                <span className="font-semibold text-emerald-200">
                  {nextMoves.find((m) => m.move_id === decision.chosen_move_id)
                    ?.label || decision.chosen_move_id}
                </span>
              </p>
            )}
            {decision.custom_note && (
              <p className="text-sm text-slate-200">
                <span className="text-slate-400">Custom Directive:</span>{" "}
                <span className="italic text-slate-100">
                  &ldquo;{decision.custom_note}&rdquo;
                </span>
              </p>
            )}
            {decision.rerun_lane_id && (
              <p className="text-sm text-slate-200">
                <span className="text-slate-400">Reran Research Lane:</span>{" "}
                <span className="font-semibold text-blue-300">
                  {decision.rerun_lane_id}
                </span>
              </p>
            )}
          </div>
        ) : isAwaiting ? (
          <div className="space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-100">
                  Select Your Next Strategic Move
                </h3>
                <p className="text-xs text-slate-400">
                  Choose a suggested path, specify custom steps, or send the
                  pipeline backwards to re-scrape a lane.
                </p>
              </div>

              {/* Mode Tabs */}
              <div className="flex items-center bg-slate-950 p-1 rounded-lg border border-slate-800 text-xs">
                <button
                  type="button"
                  onClick={() => setActiveTab("moves")}
                  className={`px-3 py-1.5 rounded-md font-medium transition ${
                    activeTab === "moves"
                      ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Recommended Moves
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("custom")}
                  className={`px-3 py-1.5 rounded-md font-medium transition ${
                    activeTab === "custom"
                      ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Custom Directive
                </button>
                <button
                  type="button"
                  onClick={() => setActiveTab("rerun")}
                  className={`px-3 py-1.5 rounded-md font-medium transition ${
                    activeTab === "rerun"
                      ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  Re-run a Lane
                </button>
              </div>
            </div>

            {/* TAB 1: Next Move Buttons */}
            {activeTab === "moves" && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                {nextMoves.map((move) => (
                  <button
                    key={move.move_id}
                    type="button"
                    disabled={isBusy}
                    onClick={() => {
                      setSelectedMoveId(move.move_id);
                      handleChooseMove(move.move_id);
                    }}
                    className="text-left p-4 rounded-xl border border-slate-800 bg-slate-950/80 hover:bg-slate-900 hover:border-amber-500/50 transition group flex flex-col justify-between focus:outline-none focus:ring-2 focus:ring-amber-500/50 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-sm font-bold text-slate-100 group-hover:text-amber-300 transition">
                          {move.label}
                        </span>
                        <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-amber-400 group-hover:translate-x-0.5 transition shrink-0" />
                      </div>
                      <p className="text-xs text-slate-400 leading-relaxed">
                        {move.rationale}
                      </p>
                    </div>

                    {selectedMoveId === move.move_id && isBusy && (
                      <div className="mt-3 pt-2 border-t border-slate-800 flex items-center gap-1.5 text-xs text-amber-400">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Confirming decision...</span>
                      </div>
                    )}
                  </button>
                ))}
              </div>
            )}

            {/* TAB 2: Custom Directive */}
            {activeTab === "custom" && (
              <form
                onSubmit={handleCustomNoteSubmit}
                className="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-3"
              >
                <div>
                  <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-1">
                    Custom Human Directive
                  </label>
                  <p className="text-xs text-slate-400 mb-2">
                    Override recommendations with your own specific next action or
                    contingency plan:
                  </p>
                  <textarea
                    value={customNote}
                    onChange={(e) => setCustomNote(e.target.value)}
                    placeholder="e.g. Schedule pilot call with 3 BisTrack distributor controllers before writing code..."
                    rows={3}
                    disabled={isBusy}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg p-3 text-sm text-slate-100 placeholder-slate-500 focus:border-amber-500 focus:ring-1 focus:ring-amber-500 outline-none resize-none"
                  />
                </div>
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={!customNote.trim() || isBusy}
                    className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 disabled:bg-slate-800 text-white disabled:text-slate-500 font-semibold text-xs flex items-center gap-2 transition"
                  >
                    {isBusy ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Send className="w-4 h-4" />
                    )}
                    <span>Submit Custom Action</span>
                  </button>
                </div>
              </form>
            )}

            {/* TAB 3: Re-run a Lane (Backwards Stepper) */}
            {activeTab === "rerun" && (
              <form
                onSubmit={handleRerunSubmit}
                className="bg-slate-950/80 border border-slate-800 rounded-xl p-5 space-y-4"
              >
                <div>
                  <div className="flex items-center gap-2 text-xs font-semibold text-blue-300 uppercase tracking-wider mb-1">
                    <RotateCcw className="w-4 h-4" />
                    <span>Send Pipeline Backwards to Research</span>
                  </div>
                  <p className="text-xs text-slate-400 mb-3">
                    Select a research lane to re-run from scratch. The agent
                    pipeline will transition backward to the{" "}
                    <code className="text-blue-300">research</code> stage and
                    re-execute Skeptic & Merge synthesis.
                  </p>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    {lanes.map((lane) => (
                      <button
                        key={lane.lane_id}
                        type="button"
                        onClick={() => setSelectedRerunLane(lane.lane_id)}
                        className={`text-left p-3 rounded-lg border text-xs transition ${
                          selectedRerunLane === lane.lane_id
                            ? "bg-blue-950/60 border-blue-500 text-blue-200 ring-1 ring-blue-500"
                            : "bg-slate-900 border-slate-800 text-slate-300 hover:border-slate-700"
                        }`}
                      >
                        <div className="font-semibold">{lane.name}</div>
                        <div className="text-[11px] text-slate-500 mt-1">
                          ID: {lane.lane_id}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={!selectedRerunLane || isBusy}
                    className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 text-white disabled:text-slate-500 font-semibold text-xs flex items-center gap-2 transition"
                  >
                    {isBusy ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <RotateCcw className="w-4 h-4" />
                    )}
                    <span>Re-run Selected Lane</span>
                  </button>
                </div>
              </form>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}
