import { describe, expect, it } from "vitest";

import { filterByTimeRange, formatDateLabel } from "./analytics-time";

interface Row {
  date: string;
  value: number;
}

const rows: Row[] = [
  { date: "2026-01-01", value: 1 },
  { date: "2026-01-15", value: 2 },
  { date: "2026-01-25", value: 3 },
  { date: "2026-01-30", value: 4 },
];

describe("filterByTimeRange", () => {
  it("returns everything for 'all'", () => {
    expect(filterByTimeRange(rows, "all")).toEqual(rows);
  });

  it("returns everything for an empty list regardless of range", () => {
    expect(filterByTimeRange([], "7d")).toEqual([]);
  });

  it("filters relative to the latest date present, not today's real date", () => {
    // Latest bucket is 2026-01-30; "7d" should keep only 2026-01-23 onward.
    const filtered = filterByTimeRange(rows, "7d");
    expect(filtered.map((r) => r.date)).toEqual(["2026-01-25", "2026-01-30"]);
  });

  it("widens correctly for a larger range", () => {
    const filtered = filterByTimeRange(rows, "30d");
    expect(filtered.map((r) => r.date)).toEqual([
      "2026-01-01",
      "2026-01-15",
      "2026-01-25",
      "2026-01-30",
    ]);
  });
});

describe("formatDateLabel", () => {
  it("formats an ISO date string as a short month/day label", () => {
    // Locale-formatted, so assert on shape rather than an exact locale string.
    const label = formatDateLabel("2026-03-05");
    expect(label).toMatch(/\d/);
    expect(label.length).toBeGreaterThan(0);
  });
});
