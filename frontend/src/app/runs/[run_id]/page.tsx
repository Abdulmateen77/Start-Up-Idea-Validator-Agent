"use client";

import React, { useEffect, useState, useCallback, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { RunView, RespondRequest } from "@/lib/types";
import { getRun, respond, streamRun } from "@/lib/api";
import { StatusBadge, StageBadge } from "@/components/Badge";
import { BriefCard } from "@/components/BriefCard";
import { IntakeChat } from "@/components/IntakeChat";
import { PipelineProgress } from "@/components/PipelineProgress";
import { HumanGateCard } from "@/components/HumanGateCard";
import { ScenarioBar } from "@/components/ScenarioBar";
import { Header } from "@/components/Header";
import {
  ArrowLeft,
  RefreshCw,
  Loader2,
  AlertTriangle,
  Radio,
  Clock,
  Calendar,
} from "lucide-react";

export default function RunDetailPage({
  params,
}: {
  params: Promise<{ run_id: string }>;
}) {
  const { run_id } = use(params);
  const router = useRouter();

  const [run, setRun] = useState<RunView | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sseConnected, setSseConnected] = useState(false);

  const fetchRun = useCallback(async () => {
    try {
      setError(null);
      const data = await getRun(run_id);
      setRun(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load run state");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [run_id]);

  // Polling layer (works standalone)
  useEffect(() => {
    fetchRun();

    const interval = setInterval(() => {
      // Keep polling active as safety net
      fetchRun();
    }, 3000);

    return () => clearInterval(interval);
  }, [fetchRun]);

  // SSE Layer (Layered on top of polling for instant liveness)
  useEffect(() => {
    const cleanup = streamRun(
      run_id,
      () => {
        setSseConnected(true);
        fetchRun();
      },
      () => {
        setSseConnected(false);
        // Fallback continues silently via polling
      }
    );

    return () => {
      cleanup();
      setSseConnected(false);
    };
  }, [run_id, fetchRun]);

  const handleIntakeAnswer = async (message: string) => {
    try {
      setError(null);
      const updated = await respond(run_id, {
        kind: "intake_answer",
        message,
      });
      setRun(updated);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to submit answer");
    }
  };

  const handleGateResponse = async (payload: RespondRequest) => {
    try {
      setError(null);
      const updated = await respond(run_id, payload);
      setRun(updated);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : "Failed to submit gate decision"
      );
    }
  };

  if (loading && !run) {
    return (
      <div className="flex-1 flex flex-col">
        <ScenarioBar />
        <Header />
        <div className="flex-1 flex items-center justify-center py-24 text-slate-400">
          <div className="text-center space-y-3">
            <Loader2 className="w-10 h-10 animate-spin mx-auto text-blue-500" />
            <p className="text-sm">Connecting to validation graph...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error && !run) {
    return (
      <div className="flex-1 flex flex-col">
        <ScenarioBar />
        <Header />
        <div className="flex-1 max-w-4xl mx-auto px-4 py-16 text-center space-y-4">
          <div className="p-4 rounded-xl bg-rose-950/60 border border-rose-500/40 text-rose-200 inline-block">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2 text-rose-400" />
            <h2 className="text-lg font-bold">Failed to load run</h2>
            <p className="text-sm mt-1">{error}</p>
          </div>
          <div>
            <Link
              href="/"
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-sm font-semibold text-white transition"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Return to Dashboard</span>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  if (!run) return null;

  const isGateAwaiting =
    run.status === "awaiting_human" && run.awaiting?.kind === "gate_decision";
  const hasRecommendation =
    run.recommendation !== null ||
    (run.awaiting && run.awaiting.kind === "gate_decision");

  const recommendationData =
    run.recommendation ||
    (run.awaiting?.kind === "gate_decision"
      ? run.awaiting.recommendation
      : null);

  const nextMovesData =
    run.awaiting?.kind === "gate_decision"
      ? run.awaiting.next_moves
      : [];

  return (
    <div className="flex-1 flex flex-col">
      <ScenarioBar />
      <Header />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Navigation & Run Meta Header */}
        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <Link
              href="/"
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400 hover:text-slate-200 transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Back to Runs</span>
            </Link>

            <div className="flex items-center gap-3">
              {/* Liveness Indicator */}
              <div
                title={
                  sseConnected
                    ? "Live SSE stream active"
                    : "Standalone Polling active"
                }
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900 border border-slate-800 text-[11px] text-slate-400"
              >
                <Radio
                  className={`w-3 h-3 ${
                    sseConnected ? "text-emerald-400 animate-pulse" : "text-amber-400"
                  }`}
                />
                <span>{sseConnected ? "SSE Live" : "Polling Active"}</span>
              </div>

              <button
                type="button"
                onClick={() => {
                  setRefreshing(true);
                  fetchRun();
                }}
                disabled={refreshing}
                title="Force refresh"
                className="p-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-slate-200 transition"
              >
                <RefreshCw
                  className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`}
                />
              </button>
            </div>
          </div>

          {/* Run Title Card */}
          <div className="rounded-xl border border-slate-800 bg-slate-900/80 p-5 shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={run.status} />
                <StageBadge stage={run.stage} />
                <span className="text-xs font-mono text-slate-500 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                  {run.run_id}
                </span>
              </div>

              <h1 className="text-lg sm:text-xl font-bold text-slate-100 leading-snug">
                {run.raw_idea}
              </h1>
            </div>

            <div className="flex flex-row md:flex-col items-start md:items-end gap-2 text-xs text-slate-400 shrink-0 border-t md:border-t-0 pt-3 md:pt-0 border-slate-800">
              <div className="flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-slate-500" />
                <span>
                  Updated:{" "}
                  {new Date(run.updated_at).toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                    second: "2-digit",
                  })}
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-slate-500">
                <Calendar className="w-3.5 h-3.5 text-slate-600" />
                <span>
                  Started: {new Date(run.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Global Error Banner (Failed state) */}
        {run.status === "failed" && run.error && (
          <div className="rounded-xl border border-rose-500/40 bg-rose-950/40 p-5 shadow-lg space-y-2">
            <div className="flex items-center gap-2 text-rose-300 font-bold text-sm uppercase tracking-wider">
              <AlertTriangle className="w-5 h-5 text-rose-400" />
              Pipeline Execution Halted with Error
            </div>
            <p className="text-sm text-rose-100 font-mono bg-rose-950/70 p-3 rounded-lg border border-rose-500/30 whitespace-pre-wrap">
              {run.error}
            </p>
          </div>
        )}

        {/* Formed Brief (if available) */}
        {run.brief && <BriefCard brief={run.brief} />}

        {/* Main Grid: Pipeline, Human Gate, and Intake Chat */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* Left Column: Progress & Human Gate Card */}
          <div
            className={`space-y-6 ${
              hasRecommendation ? "lg:col-span-8" : "lg:col-span-7"
            }`}
          >
            {/* Human Gate Card (High Priority Surface) */}
            {recommendationData && (
              <HumanGateCard
                recommendation={recommendationData}
                nextMoves={nextMovesData}
                decision={run.human_decision}
                lanes={run.lanes}
                isAwaiting={isGateAwaiting}
                onRespond={handleGateResponse}
              />
            )}

            {/* Pipeline Parallel Progress View */}
            {(run.lanes.length > 0 ||
              run.stage !== "intake" ||
              run.status === "running") && (
              <PipelineProgress
                stage={run.stage}
                status={run.status}
                lanes={run.lanes}
                laneProgress={run.lane_progress}
              />
            )}
          </div>

          {/* Right Column: Intake Chat View */}
          <div
            className={`space-y-4 ${
              hasRecommendation ? "lg:col-span-4" : "lg:col-span-5"
            }`}
          >
            <IntakeChat
              intakeTurns={run.intake_turns}
              awaiting={run.awaiting}
              status={run.status}
              onAnswer={handleIntakeAnswer}
            />
          </div>
        </div>
      </main>
    </div>
  );
}
