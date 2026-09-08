const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface ErrorEnvelope {
  error: { code: string; message: string };
}

/**
 * Client-side fetch wrapper — always sends cookies (the API is on a
 * different origin in dev) and the CSRF header the backend requires on
 * mutating requests. Never call this from a Server Component: it has no
 * access to the incoming request's cookies — use serverApiFetch instead.
 */
export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    method,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(MUTATING_METHODS.has(method) ? { "X-Requested-With": "RepoMind" } : {}),
      ...init.headers,
    },
  });

  if (!response.ok) {
    let code = "unknown_error";
    let message = response.statusText;
    try {
      const body = (await response.json()) as ErrorEnvelope;
      code = body.error?.code ?? code;
      message = body.error?.message ?? message;
    } catch {
      // Non-JSON error body (e.g. a proxy 502) — fall back to statusText.
    }
    throw new ApiError(response.status, code, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}
