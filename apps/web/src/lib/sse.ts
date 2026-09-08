const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class SseError extends Error {}

interface RawEvent {
  event: string;
  data: string;
}

/**
 * Posts to an SSE endpoint and yields parsed `{event, data}` frames as
 * they arrive. Not built on `apiFetch` (lib/api-client.ts) — that helper
 * always awaits `response.json()`, which would buffer the whole stream
 * before returning anything. This is the only streaming consumer in the
 * app, so the CSRF header and credentials mode it needs are set here
 * directly rather than factored into api-client.ts for one caller.
 */
export async function* postSSE(path: string, body: unknown): AsyncGenerator<RawEvent> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-Requested-With": "RepoMind",
    },
    body: JSON.stringify(body),
  });

  if (!response.ok || !response.body) {
    let message = response.statusText;
    try {
      const errorBody = (await response.json()) as { error?: { message?: string } };
      message = errorBody.error?.message ?? message;
    } catch {
      // Non-JSON error body — fall back to statusText.
    }
    throw new SseError(message);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let separatorIndex: number;
      while ((separatorIndex = buffer.indexOf("\n\n")) !== -1) {
        const rawFrame = buffer.slice(0, separatorIndex);
        buffer = buffer.slice(separatorIndex + 2);
        const event = parseFrame(rawFrame);
        if (event) yield event;
      }
    }
  } finally {
    reader.releaseLock();
  }
}

function parseFrame(rawFrame: string): RawEvent | null {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of rawFrame.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
    } else if (line.startsWith("data:")) {
      dataLines.push(line.slice("data:".length).trim());
    }
  }
  if (dataLines.length === 0) return null;
  return { event, data: dataLines.join("\n") };
}
