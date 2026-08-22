import { NextRequest, NextResponse } from "next/server";
import { mockStore } from "@/lib/mockStore";
import { SSEEvent } from "@/lib/types";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ run_id: string }> }
) {
  const { run_id } = await params;
  const run = mockStore.getRun(run_id);
  if (!run) {
    return NextResponse.json({ detail: "run not found" }, { status: 404 });
  }

  const encoder = new TextEncoder();
  let unsubscribe: (() => void) | null = null;
  let heartbeatTimer: NodeJS.Timeout | null = null;

  const stream = new ReadableStream({
    start(controller) {
      // Send initial state event
      const initialEvent: SSEEvent =
        run.status === "awaiting_human" && run.awaiting
          ? { event: "awaiting_human", awaiting: run.awaiting }
          : run.status === "done"
          ? { event: "run_completed", run_id: run.run_id }
          : run.status === "failed"
          ? { event: "error", detail: run.error || "run failed" }
          : { event: "stage_changed", stage: run.stage };

      controller.enqueue(
        encoder.encode(`data: ${JSON.stringify(initialEvent)}\n\n`)
      );

      // Subscribe to live run events from mock store
      unsubscribe = mockStore.subscribe(run_id, (event: SSEEvent) => {
        try {
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify(event)}\n\n`)
          );
        } catch {
          // Stream closed by client
        }
      });

      // Keepalive heartbeat
      heartbeatTimer = setInterval(() => {
        try {
          controller.enqueue(encoder.encode(": keepalive\n\n"));
        } catch {
          if (heartbeatTimer) clearInterval(heartbeatTimer);
        }
      }, 15000);

      req.signal.addEventListener("abort", () => {
        if (unsubscribe) unsubscribe();
        if (heartbeatTimer) clearInterval(heartbeatTimer);
        try {
          controller.close();
        } catch {
          // already closed
        }
      });
    },
    cancel() {
      if (unsubscribe) unsubscribe();
      if (heartbeatTimer) clearInterval(heartbeatTimer);
    },
  });

  return new NextResponse(stream, {
    headers: {
      "Content-Type": "text/event-stream; charset=utf-8",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
