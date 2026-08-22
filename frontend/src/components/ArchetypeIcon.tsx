import React from "react";
import { LaneArchetype } from "@/lib/types";
import {
  Flame,
  Swords,
  Share2,
  Scale,
  TrendingUp,
  Cpu,
  Layers,
} from "lucide-react";

interface ArchetypeBadgeProps {
  archetype: LaneArchetype;
  className?: string;
}

export function ArchetypeBadge({
  archetype,
  className = "",
}: ArchetypeBadgeProps) {
  const getArchetypeMeta = (arch: LaneArchetype) => {
    switch (arch) {
      case "customer_pain":
        return {
          label: "Customer Pain",
          icon: <Flame className="w-3.5 h-3.5 text-amber-400" />,
          classes: "bg-amber-950/40 border-amber-500/30 text-amber-300",
        };
      case "competitors":
        return {
          label: "Competitors",
          icon: <Swords className="w-3.5 h-3.5 text-rose-400" />,
          classes: "bg-rose-950/40 border-rose-500/30 text-rose-300",
        };
      case "distribution":
        return {
          label: "Distribution",
          icon: <Share2 className="w-3.5 h-3.5 text-sky-400" />,
          classes: "bg-sky-950/40 border-sky-500/30 text-sky-300",
        };
      case "regulatory":
        return {
          label: "Regulatory",
          icon: <Scale className="w-3.5 h-3.5 text-emerald-400" />,
          classes: "bg-emerald-950/40 border-emerald-500/30 text-emerald-300",
        };
      case "unit_economics":
        return {
          label: "Unit Economics",
          icon: <TrendingUp className="w-3.5 h-3.5 text-green-400" />,
          classes: "bg-green-950/40 border-green-500/30 text-green-300",
        };
      case "technical_feasibility":
        return {
          label: "Technical Feasibility",
          icon: <Cpu className="w-3.5 h-3.5 text-purple-400" />,
          classes: "bg-purple-950/40 border-purple-500/30 text-purple-300",
        };
      case "other":
      default:
        return {
          label: "Custom Lane",
          icon: <Layers className="w-3.5 h-3.5 text-slate-400" />,
          classes: "bg-slate-800/60 border-slate-700 text-slate-300",
        };
    }
  };

  const meta = getArchetypeMeta(archetype);

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium border ${meta.classes} ${className}`}
    >
      {meta.icon}
      <span>{meta.label}</span>
    </span>
  );
}
