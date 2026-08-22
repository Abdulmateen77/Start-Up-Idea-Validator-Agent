"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { RunSummary, Status } from "@/lib/types";
import { listRuns, createRun } from "@/lib/api";
import { StatusBadge, StageBadge } from "@/components/Badge";
import { ScenarioBar } from "@/components/ScenarioBar";
import { Header } from "@/components/Header";
import {
  Plus,
  Search,
  Sparkles,
  Loader2,
  ArrowUpRight,
  Filter,
  RefreshCw,
  Zap,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
} from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [rawIdea, setRawIdea] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filterStatus, setFilterStatus] = useState<Status | "all">("all");
  const [searchQuery, setSearchQuery] = useState("");

  const fetchRuns = useCallback(async () => {
    try {
      setError(null);
      const res = await listRuns();
      setRuns(res.runs);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load runs");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
    // Standalone polling on dashboard
    const interval = setInterval(fetchRuns, 5000);
    return () => clearInterval(interval);
  }, [fetchRuns]);

  const handleCreateRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!rawIdea.trim() || creating) return;

    setCreating(true);
    setError(null);
    try {
      const newRun = await createRun(rawIdea.trim());
      router.push(`/runs/${newRun.run_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to start run");
      setCreating(false);
    }
  };

  const handleExampleClick = (idea: string) => {
    setRawIdea(idea);
  };

  // Filtered runs
  const filteredRuns = runs.filter((r) => {
    const matchesFilter =
      filterStatus === "all" ? true : r.status === filterStatus;
    const matchesSearch =
      searchQuery.trim() === ""
        ? true
        : r.raw_idea.toLowerCase().includes(searchQuery.toLowerCase()) ||
          r.run_id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesFilter && matchesSearch;
  });

  const awaitingCount = runs.filter((r) => r.status === "awaiting_human").length;
  const runningCount = runs.filter((r) => r.status === "running").length;
  const doneCount = runs.filter((r) => r.status === "done").length;
  const failedCount = runs.filter((r) => r.status === "failed").length;

  return (
    <div className="flex-1 flex flex-col">
      <ScenarioBar />
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Top Hero / New Run Input */}
        <section
          id="new-run"
          className="rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900/90 to-slate-950 p-6 md:p-8 shadow-xl relative overflow-hidden"
        >
          <div className="absolute top-0 right-0 -mt-8 -mr-8 w-64 h-64 bg-blue-600/10 rounded-full blur-3xl pointer-events-none"></div>

          <div className="max-w-3xl space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-950/80 border border-blue-500/30 text-blue-300 text-xs font-semibold">
              <Zap className="w-3.5 h-3.5" />
              Evidence-Backed Idea Validator
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-100 tracking-tight">
              Validate your startup hypothesis with multi-agent research
            </h1>

            <p className="text-sm text-slate-400 leading-relaxed">
              Feed in a raw idea. The system coordinates an interactive Intake
              refinement loop, plans dynamic research lanes, scrapes verified
              sources in parallel, adversarially stress-tests all claims via a Skeptic,
              and generates a single-page Human Gate decision card.
            </p>

            <form onSubmit={handleCreateRun} className="space-y-3 pt-2">
              <div className="relative">
                <textarea
                  value={rawIdea}
                  onChange={(e) => setRawIdea(e.target.value)}
                  placeholder="e.g. AI bookkeeping and sales tax exemption agent for regional lumber distributors on BisTrack..."
                  rows={2}
                  disabled={creating}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={!rawIdea.trim() || creating}
                  className="mt-2 sm:mt-0 sm:absolute sm:right-3 sm:bottom-3 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 text-white disabled:text-slate-500 font-semibold text-xs flex items-center justify-center gap-2 shadow-lg shadow-blue-600/20 transition w-full sm:w-auto"
                >
                  {creating ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4" />
                  )}
                  <span>Start Validation Run</span>
                </button>
              </div>

              {/* Quick Examples */}
              <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-slate-500">
                <span>Quick tests:</span>
                {[
                  "AI agent for lumber sales tax exemptions",
                  "Open-source dev telemetry proxy for GDPR",
                  "Maritime crew payroll & tax automation",
                ].map((example, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => handleExampleClick(example)}
                    className="text-[11px] text-slate-400 hover:text-blue-300 bg-slate-900 border border-slate-800 hover:border-blue-500/40 px-2.5 py-1 rounded-md transition"
                  >
                    &ldquo;{example}&rdquo;
                  </button>
                ))}
              </div>
            </form>

            {error && (
              <div className="p-3.5 rounded-lg bg-rose-950/50 border border-rose-500/40 text-rose-200 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                <span>{error}</span>
              </div>
            )}
          </div>
        </section>

        {/* Stats Grid */}
        <section className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <button
            onClick={() => setFilterStatus("awaiting_human")}
            className={`p-4 rounded-xl border text-left transition ${
              filterStatus === "awaiting_human"
                ? "bg-amber-950/40 border-amber-500 ring-1 ring-amber-500"
                : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
            }`}
          >
            <div className="flex items-center justify-between text-amber-400 mb-1">
              <span className="text-xs font-semibold uppercase">
                Awaiting Human
              </span>
              <HelpCircle className="w-4 h-4" />
            </div>
            <div className="text-2xl font-bold text-slate-100">
              {awaitingCount}
            </div>
            <div className="text-[11px] text-slate-400">Intake or Gate pause</div>
          </button>

          <button
            onClick={() => setFilterStatus("running")}
            className={`p-4 rounded-xl border text-left transition ${
              filterStatus === "running"
                ? "bg-blue-950/40 border-blue-500 ring-1 ring-blue-500"
                : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
            }`}
          >
            <div className="flex items-center justify-between text-blue-400 mb-1">
              <span className="text-xs font-semibold uppercase">Running</span>
              <Loader2 className="w-4 h-4 animate-spin" />
            </div>
            <div className="text-2xl font-bold text-slate-100">
              {runningCount}
            </div>
            <div className="text-[11px] text-slate-400">Parallel research</div>
          </button>

          <button
            onClick={() => setFilterStatus("done")}
            className={`p-4 rounded-xl border text-left transition ${
              filterStatus === "done"
                ? "bg-emerald-950/40 border-emerald-500 ring-1 ring-emerald-500"
                : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
            }`}
          >
            <div className="flex items-center justify-between text-emerald-400 mb-1">
              <span className="text-xs font-semibold uppercase">Completed</span>
              <CheckCircle2 className="w-4 h-4" />
            </div>
            <div className="text-2xl font-bold text-slate-100">
              {doneCount}
            </div>
            <div className="text-[11px] text-slate-400">Decision locked</div>
          </button>

          <button
            onClick={() => setFilterStatus("failed")}
            className={`p-4 rounded-xl border text-left transition ${
              filterStatus === "failed"
                ? "bg-rose-950/40 border-rose-500 ring-1 ring-rose-500"
                : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
            }`}
          >
            <div className="flex items-center justify-between text-rose-400 mb-1">
              <span className="text-xs font-semibold uppercase">Failed</span>
              <AlertCircle className="w-4 h-4" />
            </div>
            <div className="text-2xl font-bold text-slate-100">
              {failedCount}
            </div>
            <div className="text-[11px] text-slate-400">Tool or graph error</div>
          </button>
        </section>

        {/* Runs List Section */}
        <section className="space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-slate-100">
                Validation Pipeline Runs
              </h2>
              <p className="text-xs text-slate-400">
                Showing {filteredRuns.length} of {runs.length} runs
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {/* Search */}
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search runs..."
                  className="bg-slate-900 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 outline-none focus:border-blue-500"
                />
              </div>

              {/* Status Filter Tabs */}
              <div className="flex items-center bg-slate-900 p-1 rounded-lg border border-slate-800 text-xs">
                {(["all", "awaiting_human", "running", "done", "failed"] as const).map(
                  (st) => (
                    <button
                      key={st}
                      type="button"
                      onClick={() => setFilterStatus(st)}
                      className={`px-2.5 py-1 rounded-md text-[11px] font-medium capitalize transition ${
                        filterStatus === st
                          ? "bg-slate-800 text-white font-semibold"
                          : "text-slate-400 hover:text-slate-200"
                      }`}
                    >
                      {st === "all" ? "All" : st.replace("_", " ")}
                    </button>
                  )
                )}
              </div>

              {/* Refresh Button */}
              <button
                type="button"
                onClick={() => {
                  setRefreshing(true);
                  fetchRuns();
                }}
                disabled={refreshing}
                title="Refresh runs list"
                className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 transition"
              >
                <RefreshCw
                  className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`}
                />
              </button>
            </div>
          </div>

          {/* Runs Table / Cards */}
          {loading ? (
            <div className="py-20 text-center bg-slate-900/40 rounded-xl border border-slate-800 text-slate-400">
              <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2 text-blue-500" />
              <p className="text-sm">Loading validation runs...</p>
            </div>
          ) : filteredRuns.length === 0 ? (
            <div className="py-16 text-center bg-slate-900/40 rounded-xl border border-slate-800 space-y-3">
              <HelpCircle className="w-10 h-10 mx-auto text-slate-600" />
              <div className="text-sm font-semibold text-slate-300">
                No runs found matching your filter
              </div>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                {searchQuery || filterStatus !== "all"
                  ? "Try resetting your search query or filter."
                  : "Submit a new raw idea above to start your first validation pipeline."}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3">
              {filteredRuns.map((run) => (
                <Link
                  key={run.run_id}
                  href={`/runs/${run.run_id}`}
                  className="group block p-4 sm:p-5 rounded-xl border border-slate-800 bg-slate-900/70 hover:bg-slate-900 hover:border-slate-700 transition shadow-sm hover:shadow-md"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="space-y-1.5 flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusBadge status={run.status} size="sm" />
                        <StageBadge stage={run.stage} size="sm" />
                        <span className="text-[11px] text-slate-500 font-mono">
                          {run.run_id}
                        </span>
                      </div>

                      <h3 className="text-sm sm:text-base font-semibold text-slate-100 group-hover:text-blue-300 transition truncate">
                        {run.raw_idea}
                      </h3>
                    </div>

                    <div className="flex items-center gap-4 shrink-0 sm:self-center">
                      <div className="text-right text-[11px] text-slate-400">
                        <div>
                          Updated: {new Date(run.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </div>
                        <div className="text-slate-500">
                          {new Date(run.created_at).toLocaleDateString()}
                        </div>
                      </div>

                      <div className="w-8 h-8 rounded-lg bg-slate-800 group-hover:bg-blue-600 text-slate-400 group-hover:text-white flex items-center justify-center transition">
                        <ArrowUpRight className="w-4 h-4" />
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
