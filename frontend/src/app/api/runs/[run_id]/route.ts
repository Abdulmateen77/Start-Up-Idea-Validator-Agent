import { NextRequest, NextResponse } from "next/server";
import { mockStore } from "@/lib/mockStore";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ run_id: string }> }
) {
  const { run_id } = await params;
  const run = mockStore.getRun(run_id);
  if (!run) {
    return NextResponse.json({ detail: "run not found" }, { status: 404 });
  }
  return NextResponse.json(run, { status: 200 });
}
