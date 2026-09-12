import { API_BASE_URL } from "@/lib/api-client";
import type { RealtimeEvent } from "@/lib/types";

export type ConnectionStatus = "connecting" | "open" | "reconnecting" | "closed";

const MIN_BACKOFF_MS = 1000;
const MAX_BACKOFF_MS = 30_000;
const BACKOFF_JITTER_RATIO = 0.3;

function buildWebSocketUrl(organizationId: string): string {
  const wsBase = API_BASE_URL.replace(/^http/, "ws");
  return `${wsBase}/api/v1/ws/organizations/${organizationId}`;
}

/**
 * Manages one reconnecting WebSocket to a single organization's
 * real-time channel — plain, framework-agnostic so it's easy to reason
 * about independent of React's lifecycle; lib/realtime-context.tsx owns
 * mounting/unmounting one of these per current organization.
 *
 * Reconnects with exponential backoff + jitter (capped at 30s) on any
 * unexpected close, and immediately (resetting backoff) when the browser
 * reports it's back online — a network drop and a laptop waking from
 * sleep are exactly the cases a fixed backoff alone handles poorly.
 * `stop()` is the only way to end this for good; it always clears the
 * pending reconnect timer and removes its `online` listener, so a
 * component that creates one of these in an effect and calls `stop()` in
 * the cleanup function never leaks a timer or a listener.
 */
export class RealtimeConnection {
  private ws: WebSocket | null = null;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private backoffMs = MIN_BACKOFF_MS;
  private stopped = false;

  constructor(
    private readonly organizationId: string,
    private readonly onStatusChange: (status: ConnectionStatus) => void,
    private readonly onEvent: (event: RealtimeEvent) => void,
  ) {}

  start(): void {
    this.stopped = false;
    window.addEventListener("online", this.handleOnline);
    this.connect();
  }

  stop(): void {
    this.stopped = true;
    window.removeEventListener("online", this.handleOnline);
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  private handleOnline = (): void => {
    if (this.stopped) return;
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.backoffMs = MIN_BACKOFF_MS;
    this.connect();
  };

  private connect(): void {
    if (this.stopped) return;
    this.onStatusChange("connecting");

    const ws = new WebSocket(buildWebSocketUrl(this.organizationId));
    this.ws = ws;

    ws.onopen = () => {
      this.backoffMs = MIN_BACKOFF_MS;
      this.onStatusChange("open");
    };

    ws.onmessage = (message) => {
      let parsed: { category?: string } | null = null;
      try {
        parsed = JSON.parse(message.data as string);
      } catch {
        return; // Malformed message — drop it, never crash the connection.
      }
      if (!parsed || parsed.category === "ping") return;
      this.onEvent(parsed as RealtimeEvent);
    };

    ws.onclose = () => {
      // A newer connection has already replaced this one (e.g. an
      // `online` event fired mid-connect) — this stale socket's close
      // must not stomp on that newer connection's state.
      if (this.ws !== ws) return;
      this.ws = null;

      if (this.stopped) {
        this.onStatusChange("closed");
        return;
      }
      this.onStatusChange("reconnecting");
      this.scheduleReconnect();
    };
  }

  private scheduleReconnect(): void {
    const jitter = Math.random() * BACKOFF_JITTER_RATIO * this.backoffMs;
    const delay = this.backoffMs + jitter;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
    this.backoffMs = Math.min(this.backoffMs * 2, MAX_BACKOFF_MS);
  }
}
