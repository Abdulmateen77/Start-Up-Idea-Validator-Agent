import React from "react";
import { IdeaBrief } from "@/lib/types";
import { Sparkles, Target, Users, HelpCircle } from "lucide-react";

interface BriefCardProps {
  brief: IdeaBrief;
}

export function BriefCard({ brief }: BriefCardProps) {
  return (
    <div className="rounded-xl border border-indigo-500/30 bg-gradient-to-br from-indigo-950/40 via-slate-900 to-slate-950 p-5 shadow-lg shadow-indigo-950/20">
      <div className="flex items-center gap-2 mb-4 pb-3 border-b border-indigo-500/20">
        <div className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400">
          <Sparkles className="w-4 h-4" />
        </div>
        <h3 className="text-sm font-semibold uppercase tracking-wider text-indigo-300">
          Validated Idea Brief
        </h3>
        <span className="text-xs text-slate-400 ml-auto">
          Generated via Intake Synthesis
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3.5">
          <div className="flex items-center gap-1.5 text-xs font-medium text-slate-400 mb-1">
            <Target className="w-3.5 h-3.5 text-indigo-400" />
            <span>Target Niche</span>
          </div>
          <p className="text-sm font-medium text-slate-200">{brief.niche}</p>
        </div>

        <div className="bg-slate-900/80 border border-slate-800 rounded-lg p-3.5">
          <div className="flex items-center gap-1.5 text-xs font-medium text-slate-400 mb-1">
            <Users className="w-3.5 h-3.5 text-indigo-400" />
            <span>Target Audience / Buyer</span>
          </div>
          <p className="text-sm font-medium text-slate-200">{brief.audience}</p>
        </div>
      </div>

      <div className="bg-indigo-950/30 border border-indigo-500/20 rounded-lg p-3.5">
        <div className="flex items-center gap-1.5 text-xs font-medium text-indigo-300 mb-1">
          <HelpCircle className="w-3.5 h-3.5 text-indigo-400" />
          <span>Core Hypothesis / Research Question</span>
        </div>
        <p className="text-sm font-medium text-indigo-100 italic">
          &ldquo;{brief.core_question}&rdquo;
        </p>
      </div>
    </div>
  );
}
