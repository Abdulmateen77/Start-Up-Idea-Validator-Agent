import { NextResponse } from "next/server";
import { mockStore } from "@/lib/mockStore";

export async function POST() {
  mockStore.resetToPresets();
  const runs = mockStore.listRuns();
  return NextResponse.json({ success: true, runs });
}
