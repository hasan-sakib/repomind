import type { DailyCommit, DailyPRIssueActivity } from "@/lib/types";

export interface MergedDailyActivity {
  date: string;
  commits: number;
  prs_opened: number;
  prs_merged: number;
  prs_closed: number;
  issues_opened: number;
}

/** Merges the per-(day, author) commit buckets with the per-day PR/issue
 * buckets into one row per day for the combined activity chart. PR/issue
 * counts are never broken down by author (the snapshot doesn't track
 * that), so they're always repo-wide regardless of `contributorLogin`. */
export function mergeDailyActivity(
  dailyCommits: DailyCommit[],
  dailyPrIssue: DailyPRIssueActivity[],
  contributorLogin: string | null,
): MergedDailyActivity[] {
  const commitsByDate = new Map<string, number>();
  for (const c of dailyCommits) {
    if (contributorLogin !== null && c.login !== contributorLogin) continue;
    commitsByDate.set(c.date, (commitsByDate.get(c.date) ?? 0) + c.count);
  }
  const prByDate = new Map(dailyPrIssue.map((d) => [d.date, d]));
  const allDates = new Set([...commitsByDate.keys(), ...prByDate.keys()]);

  return Array.from(allDates)
    .sort()
    .map((date) => ({
      date,
      commits: commitsByDate.get(date) ?? 0,
      prs_opened: prByDate.get(date)?.prs_opened ?? 0,
      prs_merged: prByDate.get(date)?.prs_merged ?? 0,
      prs_closed: prByDate.get(date)?.prs_closed ?? 0,
      issues_opened: prByDate.get(date)?.issues_opened ?? 0,
    }));
}

export interface DailyCommitTotal {
  date: string;
  count: number;
}

export function sumDailyCommits(
  dailyCommits: DailyCommit[],
  contributorLogin: string | null,
): DailyCommitTotal[] {
  const byDate = new Map<string, number>();
  for (const c of dailyCommits) {
    if (contributorLogin !== null && c.login !== contributorLogin) continue;
    byDate.set(c.date, (byDate.get(c.date) ?? 0) + c.count);
  }
  return Array.from(byDate.entries())
    .sort(([a], [b]) => (a < b ? -1 : 1))
    .map(([date, count]) => ({ date, count }));
}
