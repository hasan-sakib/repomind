import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { formatRelativeTime } from "./format-time";

const NOW = new Date("2026-06-15T12:00:00Z");

beforeEach(() => {
  vi.useFakeTimers();
  vi.setSystemTime(NOW);
});

afterEach(() => {
  vi.useRealTimers();
});

describe("formatRelativeTime", () => {
  it("returns 'Never' for null", () => {
    expect(formatRelativeTime(null)).toBe("Never");
  });

  it("returns 'just now' for under a minute ago", () => {
    const iso = new Date(NOW.getTime() - 10_000).toISOString();
    expect(formatRelativeTime(iso)).toBe("just now");
  });

  it("formats minutes ago", () => {
    const iso = new Date(NOW.getTime() - 5 * 60_000).toISOString();
    expect(formatRelativeTime(iso)).toBe("5m ago");
  });

  it("formats hours ago", () => {
    const iso = new Date(NOW.getTime() - 3 * 60 * 60_000).toISOString();
    expect(formatRelativeTime(iso)).toBe("3h ago");
  });

  it("formats days ago", () => {
    const iso = new Date(NOW.getTime() - 5 * 24 * 60 * 60_000).toISOString();
    expect(formatRelativeTime(iso)).toBe("5d ago");
  });

  it("falls back to a calendar date beyond 30 days", () => {
    const iso = new Date(NOW.getTime() - 45 * 24 * 60 * 60_000).toISOString();
    const result = formatRelativeTime(iso);
    expect(result).not.toMatch(/ago$/);
    expect(result.length).toBeGreaterThan(0);
  });
});
