"use client";

import React, { useState, useRef, useEffect } from "react";
import { IntakeTurn, Awaiting, Status } from "@/lib/types";
import { Bot, User, Send, Loader2, Sparkles, MessageSquare } from "lucide-react";

interface IntakeChatProps {
  intakeTurns: IntakeTurn[];
  awaiting: Awaiting | null;
  status: Status;
  onAnswer: (message: string) => Promise<void>;
  isLoading?: boolean;
}

export function IntakeChat({
  intakeTurns,
  awaiting,
  status,
  onAnswer,
  isLoading = false,
}: IntakeChatProps) {
  const [inputMessage, setInputMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll when turns or awaiting status change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [intakeTurns.length, awaiting]);

  const isAwaitingIntake =
    status === "awaiting_human" && awaiting?.kind === "intake_question";

  const isBusy = status === "running" || submitting || isLoading;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputMessage.trim() || !isAwaitingIntake || isBusy) return;

    const msg = inputMessage.trim();
    setInputMessage("");
    setSubmitting(true);
    try {
      await onAnswer(msg);
    } finally {
      setSubmitting(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-lg backdrop-blur-sm">
      {/* Chat Header */}
      <div className="px-5 py-3.5 border-b border-slate-800 bg-slate-900/90 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-purple-500/20 text-purple-400">
            <MessageSquare className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              Intake Clarification
              {isAwaitingIntake && (
                <span className="text-[11px] font-medium text-amber-400 bg-amber-950/60 border border-amber-500/30 px-2 py-0.5 rounded-full">
                  Question Active
                </span>
              )}
            </h3>
            <p className="text-xs text-slate-400">
              Interactive refinement loop to pin down niche, buyer, & core hypothesis
            </p>
          </div>
        </div>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4 min-h-[300px] max-h-[500px]">
        {intakeTurns.length === 0 ? (
          <div className="text-center py-12 text-slate-500">
            <Bot className="w-10 h-10 mx-auto mb-2 text-slate-600 animate-pulse" />
            <p className="text-sm">Initiating intake conversation...</p>
          </div>
        ) : (
          intakeTurns.map((turn, index) => {
            const isAgent = turn.role === "agent";
            return (
              <div
                key={index}
                className={`flex gap-3 ${
                  isAgent ? "items-start" : "items-start flex-row-reverse"
                }`}
              >
                <div
                  className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                    isAgent
                      ? "bg-purple-950 border border-purple-500/40 text-purple-300"
                      : "bg-blue-950 border border-blue-500/40 text-blue-300"
                  }`}
                >
                  {isAgent ? (
                    <Bot className="w-4 h-4" />
                  ) : (
                    <User className="w-4 h-4" />
                  )}
                </div>

                <div
                  className={`max-w-[85%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
                    isAgent
                      ? "bg-slate-800/90 border border-slate-700 text-slate-100 rounded-tl-none shadow-md"
                      : "bg-blue-600 text-white rounded-tr-none shadow-md shadow-blue-900/30"
                  }`}
                >
                  <div className="text-[11px] font-semibold tracking-wider uppercase mb-1 opacity-70">
                    {isAgent ? "Intake Agent" : "Founder / Human"}
                  </div>
                  <div className="whitespace-pre-wrap">{turn.content}</div>
                </div>
              </div>
            );
          })
        )}

        {/* Running spinner indicator when processing */}
        {status === "running" && (
          <div className="flex gap-3 items-start">
            <div className="w-8 h-8 rounded-lg bg-purple-950 border border-purple-500/40 text-purple-300 flex items-center justify-center shrink-0 animate-pulse">
              <Sparkles className="w-4 h-4 text-purple-400" />
            </div>
            <div className="bg-slate-800/80 border border-slate-700 rounded-xl rounded-tl-none px-4 py-3 text-sm text-slate-300 flex items-center gap-2.5">
              <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
              <span>Intake Agent is analyzing your reply and synthesizing next steps...</span>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input Form */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/95">
        {isAwaitingIntake ? (
          <form onSubmit={handleSubmit} className="flex flex-col gap-2">
            <div className="flex items-center gap-1.5 text-xs text-amber-400 font-medium px-1">
              <span>Your response is needed to proceed</span>
            </div>
            <div className="relative flex items-center">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your clarification or target audience details..."
                disabled={isBusy}
                rows={2}
                className="w-full bg-slate-950 border border-slate-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 rounded-lg px-3.5 py-2.5 pr-24 text-sm text-slate-100 placeholder-slate-500 resize-none outline-none transition disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button
                type="submit"
                disabled={!inputMessage.trim() || isBusy}
                className="absolute right-2.5 bottom-2.5 px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-500 disabled:bg-slate-800 text-white disabled:text-slate-500 font-medium text-xs flex items-center gap-1.5 transition shadow-sm"
              >
                {submitting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Send className="w-3.5 h-3.5" />
                )}
                <span>Send</span>
              </button>
            </div>
            <div className="flex justify-between items-center px-1 text-[11px] text-slate-500">
              <span>Press Enter to send, Shift+Enter for new line</span>
              <span>Loop continues until hypothesis is concrete</span>
            </div>
          </form>
        ) : (
          <div className="text-center py-2 px-3 bg-slate-950/50 rounded-lg border border-slate-800/80 text-xs text-slate-400">
            {status === "running" ? (
              <span className="flex items-center justify-center gap-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-400" />
                Pipeline running. Intake turns are locked while agents execute.
              </span>
            ) : status === "done" ? (
              <span>Intake phase completed. See full recommendation above.</span>
            ) : (
              <span>Intake turns completed.</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
