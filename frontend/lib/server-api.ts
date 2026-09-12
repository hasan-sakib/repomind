import "server-only";

import { cookies } from "next/headers";

import { ApiError } from "@/lib/api-client";

// This fetch runs inside the Next.js server process, not the browser — in
// Docker, "localhost" there means the `web` container itself, not the
// `api` container, which is why this can't just reuse
// NEXT_PUBLIC_API_URL (the browser-facing, host-reachable URL, baked into
// the client bundle at build time). API_INTERNAL_URL is a plain
// (non-NEXT_PUBLIC_) server-only env var so it can be set per-environment
// at *runtime* without rebuilding the image — docker-compose.yml sets it
// to `http://api:8000` (the compose network's service DNS name) for the
// `web` service; local (non-Docker) dev has no such distinction, so it
// falls back to NEXT_PUBLIC_API_URL.
const API_BASE_URL =
  process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ErrorEnvelope {
  error: { code: string; message: string };
}

/**
 * Server Component fetch wrapper. A Server Component's own `fetch` never
 * automatically carries the browser's cookies to a different-origin API —
 * the incoming request's cookies must be forwarded explicitly.
 */
export async function serverApiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const cookieStore = await cookies();
  const cookieHeader = cookieStore
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Cookie: cookieHeader,
      ...init.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let code = "unknown_error";
    let message = response.statusText;
    try {
      const body = (await response.json()) as ErrorEnvelope;
      code = body.error?.code ?? code;
      message = body.error?.message ?? message;
    } catch {
      // Non-JSON error body — fall back to statusText.
    }
    throw new ApiError(response.status, code, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}
