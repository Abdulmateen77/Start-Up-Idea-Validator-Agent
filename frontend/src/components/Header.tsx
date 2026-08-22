import React from "react";
import Link from "next/link";
import { ShieldCheck, Plus, Sparkles, LayoutDashboard } from "lucide-react";

interface HeaderProps {
  onNewRunClick?: () => void;
}

export function Header({ onNewRunClick }: HeaderProps) {
  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-md sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link
          href="/"
          className="flex items-center gap-3 group transition"
        >
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-blue-500/20 group-hover:scale-105 transition">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <div className="text-base font-bold text-slate-100 flex items-center gap-2">
              Idea Validator Agent
              <span className="text-[10px] font-semibold uppercase tracking-wider bg-blue-950 text-blue-400 border border-blue-500/30 px-1.5 py-0.5 rounded">
                v1.0
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">
              Evidence-backed validation graph with human-in-the-loop gating
            </p>
          </div>
        </Link>

        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="px-3 py-1.5 rounded-lg border border-slate-800 text-xs font-medium text-slate-300 hover:text-white hover:bg-slate-900 transition flex items-center gap-1.5"
          >
            <LayoutDashboard className="w-3.5 h-3.5" />
            <span>Dashboard</span>
          </Link>

          {onNewRunClick ? (
            <button
              type="button"
              onClick={onNewRunClick}
              className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-sm flex items-center gap-1.5 transition"
            >
              <Plus className="w-4 h-4" />
              <span>New Run</span>
            </button>
          ) : (
            <Link
              href="/#new-run"
              className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-sm flex items-center gap-1.5 transition"
            >
              <Plus className="w-4 h-4" />
              <span>New Run</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
