import { TIME_RANGE_LABELS, type TimeRange } from "@/lib/analytics-time";
import { cn } from "cn";

const RANGES: TimeRange[] = ["7d", "30d", "90d", "all"];

export function TimeRangeToggle({
  value,
  onChange,
}: {
  value: TimeRange;
  onChange: (range: TimeRange) => void;
}) {
  return (
    <div className="flex gap-1.5" role="group" aria-label="Time range">
      {RANGES.map((range) => (
        <button
          key={range}
          type="button"
          onClick={() => onChange(range)}
          className={cn(
            "rounded-full border px-2.5 py-1 text-xs font-medium transition-colors",
            value === range
              ? "border-brand bg-brand/10 text-brand"
              : "border-border text-muted-foreground hover:text-foreground",
          )}
        >
          {TIME_RANGE_LABELS[range]}
        </button>
      ))}
    </div>
  );
}
