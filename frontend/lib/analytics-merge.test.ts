import { describe, expect, it } from "vitest";

import { mergeDailyActivity, sumDailyCommits } from "./analytics-merge";
import type { DailyCommit, DailyPRIssueActivity } from "@/lib/types";

const dailyCommits: DailyCommit[] = [
  { date: "2026-01-01", login: "alice", name: "Alice", count: 3 },
  { date: "2026-01-01", login: "bob", name: "Bob", count: 2 },
  { date: "2026-01-02", login: "alice", name: "Alice", count: 1 },
];

const dailyPrIssue: DailyPRIssueActivity[] = [
  { date: "2026-01-01", prs_opened: 2, prs_merged: 1, prs_closed: 0, issues_opened: 1 },
  { date: "2026-01-03", prs_opened: 0, prs_merged: 0, prs_closed: 1, issues_opened: 0 },
];

describe("mergeDailyActivity", () => {
  it("sums commits per day across all contributors when none is selected", () => {
    const merged = mergeDailyActivity(dailyCommits, dailyPrIssue, null);
    const jan1 = merged.find((r) => r.date === "2026-01-01");
    expect(jan1?.commits).toBe(5);
  });

  it("filters commits to a single contributor when one is selected", () => {
    const merged = mergeDailyActivity(dailyCommits, dailyPrIssue, "alice");
    const jan1 = merged.find((r) => r.date === "2026-01-01");
    expect(jan1?.commits).toBe(3);
  });

  it("never filters PR/issue counts by contributor (not tracked per-author)", () => {
    const merged = mergeDailyActivity(dailyCommits, dailyPrIssue, "alice");
    const jan1 = merged.find((r) => r.date === "2026-01-01");
    expect(jan1?.prs_opened).toBe(2);
  });

  it("includes a day that only has PR/issue activity, with zero commits", () => {
    const merged = mergeDailyActivity(dailyCommits, dailyPrIssue, null);
    const jan3 = merged.find((r) => r.date === "2026-01-03");
    expect(jan3).toEqual({
      date: "2026-01-03",
      commits: 0,
      prs_opened: 0,
      prs_merged: 0,
      prs_closed: 1,
      issues_opened: 0,
    });
  });

  it("returns rows sorted by date ascending", () => {
    const merged = mergeDailyActivity(dailyCommits, dailyPrIssue, null);
    const dates = merged.map((r) => r.date);
    expect(dates).toEqual([...dates].sort());
  });

  it("returns an empty list for no input", () => {
    expect(mergeDailyActivity([], [], null)).toEqual([]);
  });
});

describe("sumDailyCommits", () => {
  it("sums per day across contributors", () => {
    const totals = sumDailyCommits(dailyCommits, null);
    expect(totals).toEqual([
      { date: "2026-01-01", count: 5 },
      { date: "2026-01-02", count: 1 },
    ]);
  });

  it("filters to a single contributor", () => {
    const totals = sumDailyCommits(dailyCommits, "bob");
    expect(totals).toEqual([{ date: "2026-01-01", count: 2 }]);
  });
});
