import {
  RunView,
  ListRunsResponse,
  CreateRunRequest,
  RespondRequest,
  SSEEvent,
} from "./types";

function getBaseUrl(): string {
  // Base URL comes from NEXT_PUBLIC_API_BASE. If unset, use relative "/api" route handlers.
  const envBase = process.env.NEXT_PUBLIC_API_BASE;
  if (envBase && envBase.trim() !== "") {
    return envBase.replace(/\/+$/, "");
  }
  return "/api";
}

export class ApiError extends Error {
  constructor(public status: number, public detail: string) {
    super(`API Error ${status}: ${detail}`);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = `HTTP ${res.status} ${res.statusText}`;
    try {
      const errorJson = await res.json();
      if (errorJson && typeof errorJson.detail === "string") {
        detail = errorJson.detail;
      }
    } catch {
      // Body not JSON
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export async function createRun(raw_idea: string): Promise<RunView> {
  const base = getBaseUrl();
  const payload: CreateRunRequest = { raw_idea };
  const res = await fetch(`${base}/runs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return handleResponse<RunView>(res);
}

export async function listRuns(): Promise<ListRunsResponse> {
  const base = getBaseUrl();
  const res = await fetch(`${base}/runs`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    cache: "no-store",
  });
  return handleResponse<ListRunsResponse>(res);
}

export async function getRun(run_id: string): Promise<RunView> {
  const base = getBaseUrl();
  const res = await fetch(`${base}/runs/${encodeURIComponent(run_id)}`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
    cache: "no-store",
  });
  return handleResponse<RunView>(res);
}

export async function respond(
  run_id: string,
  payload: RespondRequest
): Promise<RunView> {
  const base = getBaseUrl();
  const res = await fetch(
    `${base}/runs/${encodeURIComponent(run_id)}/respond`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }
  );
  return handleResponse<RunView>(res);
}

export async function resetMockRuns(): Promise<ListRunsResponse> {
  const base = getBaseUrl();
  const res = await fetch(`${base}/runs/reset`, {
    method: "POST",
  });
  return handleResponse<ListRunsResponse>(res);
}

/**
 * SSE listener layered on top of polling.
 * When SSE connects, it emits events live.
 * If connection fails or closes, caller's polling keeps running safely.
 */
export function streamRun(
  run_id: string,
  onEvent: (event: SSEEvent) => void,
  onError?: (error: Error) => void
): () => void {
  const base = getBaseUrl();
  const streamUrl = `${base}/runs/${encodeURIComponent(run_id)}/stream`;

  let eventSource: EventSource | null = null;
  let isClosed = false;

  try {
    eventSource = new EventSource(streamUrl);

    eventSource.onmessage = (e) => {
      if (isClosed) return;
      try {
        if (!e.data || e.data.startsWith(":")) return;
        const parsed = JSON.parse(e.data) as SSEEvent;
        onEvent(parsed);
      } catch (err: unknown) {
        if (onError && err instanceof Error) {
          onError(err);
        }
      }
    };

    eventSource.onerror = (err) => {
      if (isClosed) return;
      if (onError) {
        onError(new Error("SSE stream disconnected or failed"));
      }
    };
  } catch (err: unknown) {
    if (onError && err instanceof Error) {
      onError(err);
    }
  }

  return () => {
    isClosed = true;
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
  };
}
