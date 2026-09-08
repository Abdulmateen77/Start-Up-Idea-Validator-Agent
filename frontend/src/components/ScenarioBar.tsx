"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Beaker, RotateCcw, Sparkles } from "lucide-react";
import { isLiveBackend, resetMockRuns } from "@/lib/api";

const SCENARIOS = [
  {
    id: "mock-intake-loop",
    label: "Intake Loop (Turn 3)",
    desc: "Unbounded intake QA pause",
    badge: "Intake",
  },
  {
    id: "mock-2-lane-active",
    label: "2-Lane Run",
    desc: "Parallel 2-vector search",
    badge: "Running",
  },
  {
    id: "mock-5-lane-rich",
    label: "5-Lane Fan-out",
    desc: "Parallel 5-vector search",
    badge: "Running",
  },
  {
    id: "mock-all-other-archetypes",
    label: 'All "Other" Archetypes',
    desc: "Custom non-standard archetypes",
    badge: "Custom",
  },
  {
    id: "mock-edge-evidence-and-failure",
    label: "No Evidence vs Tool Failure",
    desc: "0 claims found & tool error",
    badge: "Edge Case",
  },
  {
    id: "mock-gate-decision-ready",
    label: "Gate Decision Ready",
    desc: "Recommendation & 4 moves",
    badge: "Gate",
  },
  {
    id: "mock-gate-not-enough-evidence",
    label: 'Verdict: "Not Enough Evidence"',
    desc: "Legitimate non-error verdict",
    badge: "Gate",
  },
  {
    id: "mock-run-failed",
    label: "Failed Run (Error State)",
    desc: "Execution halted with error",
    badge: "Failed",
  },
  {
    id: "mock-run-completed-decision",
    label: "Completed Run",
    desc: "Human decision recorded",
    badge: "Done",
  },
];

export function ScenarioBar() {
  const pathname = usePathname();

  // Mock-only affordance. Against a real backend these scenarios are meaningless
  // (and would inject fake runs next to real ones), so the bar hides itself
  // rather than every caller having to remember to guard it.
  if (isLiveBackend()) {
    return null;
  }

  const handleResetPresets = async () => {
    try {
      await resetMockRuns();
      window.location.href = "/";
    } catch {
      window.location.reload();
    }
  };

  return (
    <div className="bg-slate-900/90 border-b border-slate-800 text-xs py-2.5 px-4 sticky top-0 z-40 backdrop-blur-md">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-2.5">
        <div className="flex items-center gap-2 text-slate-300 font-semibold shrink-0">
          <Beaker className="w-4 h-4 text-amber-400" />
          <span className="text-amber-300">Mock Matrix Scenarios:</span>
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 md:pb-0 scrollbar-none">
          {SCENARIOS.map((sc) => {
            const isActive = pathname === `/runs/${sc.id}`;
            return (
              <Link
                key={sc.id}
                href={`/runs/${sc.id}`}
                title={sc.desc}
                className={`whitespace-nowrap px-2.5 py-1 rounded-md text-[11px] font-medium border transition shrink-0 ${
                  isActive
                    ? "bg-amber-500/20 border-amber-500/50 text-amber-200 ring-1 ring-amber-500/40"
                    : "bg-slate-950/60 border-slate-800 text-slate-300 hover:text-white hover:border-slate-700"
                }`}
              >
                {sc.label}
              </Link>
            );
          })}
        </div>

        <button
          type="button"
          onClick={handleResetPresets}
          title="Reset all mock runs back to initial fixtures"
          className="self-end md:self-auto inline-flex items-center gap-1 px-2 py-1 rounded text-[11px] text-slate-400 hover:text-slate-200 bg-slate-950 border border-slate-800 hover:border-slate-700 transition shrink-0"
        >
          <RotateCcw className="w-3 h-3" />
          <span>Reset Mocks</span>
        </button>
      </div>
    </div>
  );
}
