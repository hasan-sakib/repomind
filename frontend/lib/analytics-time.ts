export type TimeRange = "7d" | "30d" | "90d" | "all";

export const TIME_RANGE_LABELS: Record<TimeRange, string> = {
  "7d": "7 days",
  "30d": "30 days",
  "90d": "90 days",
  all: "All time",
};

const TIME_RANGE_DAYS: Record<TimeRange, number | null> = {
  "7d": 7,
  "30d": 30,
  "90d": 90,
  all: null,
};

/** Filters any date-bucketed record list down to the selected window,
 * comparing against the latest date actually present in the data (not
 * "today") — a snapshot is generated at a point in time, so "last 7
 * days" means the 7 days before its most recent bucket, not before now. */
export function filterByTimeRange<T extends { date: string }>(
  records: T[],
  range: TimeRange,
): T[] {
  const days = TIME_RANGE_DAYS[range];
  if (days === null || records.length === 0) return records;
  const latest = records.reduce((max, r) => (r.date > max ? r.date : max), records[0].date);
  const cutoff = new Date(latest);
  cutoff.setDate(cutoff.getDate() - days);
  const cutoffStr = cutoff.toISOString().slice(0, 10);
  return records.filter((r) => r.date >= cutoffStr);
}

export function formatDateLabel(dateStr: string): string {
  const date = new Date(`${dateStr}T00:00:00`);
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}
