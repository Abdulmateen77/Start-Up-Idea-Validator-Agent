import { NextRequest, NextResponse } from "next/server";
import { mockStore } from "@/lib/mockStore";
import { CreateRunRequest } from "@/lib/types";

export async function GET() {
  const runs = mockStore.listRuns();
  return NextResponse.json({ runs });
}

export async function POST(req: NextRequest) {
  try {
    const body: CreateRunRequest = await req.json();
    if (!body || typeof body.raw_idea !== "string" || !body.raw_idea.trim()) {
      return NextResponse.json(
        { detail: "raw_idea must be a non-empty string" },
        { status: 422 }
      );
    }

    const run = mockStore.createRun(body.raw_idea.trim());
    return NextResponse.json(run, { status: 201 });
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : "Internal server error";
    return NextResponse.json({ detail: message }, { status: 500 });
  }
}
