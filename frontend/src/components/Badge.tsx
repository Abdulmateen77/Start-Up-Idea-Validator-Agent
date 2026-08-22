import React from "react";
import { Status, Stage } from "@/lib/types";
import {
  Clock,
  CheckCircle2,
  AlertCircle,
  PlayCircle,
  HelpCircle,
  Sparkles,
  Search,
  ShieldCheck,
  GitMerge,
  Award,
} from "lucide-react";

interface StatusBadgeProps {
  status: Status;
  size?: "sm" | "md";
}

export function StatusBadge({ status, size = "md" }: StatusBadgeProps) {
  const sizeClasses =
    size === "sm"
      ? "px-2 py-0.5 text-xs gap-1"
      : "px-2.5 py-1 text-xs font-medium gap-1.5";

  switch (status) {
    case "running":
      return (
        <span
          className={`inline-flex items-center rounded-full bg-blue-950/80 border border-blue-500/40 text-blue-300 font-medium ${sizeClasses}`}
        >
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
          </span>
          Running
        </span>
      );
    case "awaiting_human":
      return (
        <span
          className={`inline-flex items-center rounded-full bg-amber-950/80 border border-amber-500/40 text-amber-300 font-medium shadow-sm shadow-amber-900/20 ${sizeClasses}`}
        >
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
          </span>
          <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
          Awaiting Human Input
        </span>
      );
    case "done":
      return (
        <span
          className={`inline-flex items-center rounded-full bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 font-medium ${sizeClasses}`}
        >
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          Completed
        </span>
      );
    case "failed":
      return (
        <span
          className={`inline-flex items-center rounded-full bg-rose-950/80 border border-rose-500/40 text-rose-300 font-medium ${sizeClasses}`}
        >
          <AlertCircle className="w-3.5 h-3.5 text-rose-400" />
          Failed
        </span>
      );
    default:
      return (
        <span
          className={`inline-flex items-center rounded-full bg-slate-800 border border-slate-700 text-slate-300 ${sizeClasses}`}
        >
          {status}
        </span>
      );
  }
}

interface StageBadgeProps {
  stage: Stage;
  size?: "sm" | "md";
}

export function StageBadge({ stage, size = "md" }: StageBadgeProps) {
  const sizeClasses =
    size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs";

  const getStageMeta = (s: Stage) => {
    switch (s) {
      case "intake":
        return {
          label: "Intake",
          icon: <HelpCircle className="w-3.5 h-3.5" />,
          classes: "bg-purple-950/70 border-purple-500/30 text-purple-300",
        };
      case "plan":
        return {
          label: "Plan",
          icon: <Sparkles className="w-3.5 h-3.5" />,
          classes: "bg-indigo-950/70 border-indigo-500/30 text-indigo-300",
        };
      case "research":
        return {
          label: "Research (Parallel)",
          icon: <Search className="w-3.5 h-3.5" />,
          classes: "bg-blue-950/70 border-blue-500/30 text-blue-300",
        };
      case "skeptic":
        return {
          label: "Skeptic Review",
          icon: <ShieldCheck className="w-3.5 h-3.5" />,
          classes: "bg-cyan-950/70 border-cyan-500/30 text-cyan-300",
        };
      case "merge":
        return {
          label: "Merge Synthesis",
          icon: <GitMerge className="w-3.5 h-3.5" />,
          classes: "bg-violet-950/70 border-violet-500/30 text-violet-300",
        };
      case "human_gate":
        return {
          label: "Human Gate",
          icon: <Award className="w-3.5 h-3.5" />,
          classes: "bg-amber-950/70 border-amber-500/30 text-amber-300",
        };
      case "done":
        return {
          label: "Done",
          icon: <CheckCircle2 className="w-3.5 h-3.5" />,
          classes: "bg-emerald-950/70 border-emerald-500/30 text-emerald-300",
        };
      case "failed":
        return {
          label: "Failed",
          icon: <AlertCircle className="w-3.5 h-3.5" />,
          classes: "bg-rose-950/70 border-rose-500/30 text-rose-300",
        };
      default:
        return {
          label: s,
          icon: <Clock className="w-3.5 h-3.5" />,
          classes: "bg-slate-800 border-slate-700 text-slate-300",
        };
    }
  };

  const meta = getStageMeta(stage);

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border font-medium uppercase tracking-wider ${meta.classes} ${sizeClasses}`}
    >
      {meta.icon}
      {meta.label}
    </span>
  );
}
