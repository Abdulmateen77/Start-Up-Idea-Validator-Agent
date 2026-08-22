import { NextRequest, NextResponse } from "next/server";
import { mockStore } from "@/lib/mockStore";
import { RespondRequest } from "@/lib/types";

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ run_id: string }> }
) {
  const { run_id } = await params;
  try {
    const body: RespondRequest = await req.json();
    if (!body || !body.kind) {
      return NextResponse.json(
        { detail: "missing or invalid 'kind' field in request" },
        { status: 422 }
      );
    }

    const updatedRun = mockStore.respond(run_id, body);
    return NextResponse.json(updatedRun, { status: 200 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal server error";
    if (message === "run not found") {
      return NextResponse.json({ detail: message }, { status: 404 });
    }
    if (message === "run is not awaiting human input") {
      return NextResponse.json({ detail: message }, { status: 409 });
    }
    if (
      message.startsWith("wrong kind") ||
      message.startsWith("invalid respond payload")
    ) {
      return NextResponse.json({ detail: message }, { status: 422 });
    }
    return NextResponse.json({ detail: message }, { status: 500 });
  }
}
