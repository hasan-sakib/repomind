import type { TooltipContentProps } from "recharts";

import { formatDateLabel } from "@/lib/analytics-time";

export function ChartTooltip({
  active,
  payload,
  label,
}: Partial<TooltipContentProps<number, string>>) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border border-border bg-popover px-3 py-2 text-xs shadow-md">
      {label && (
        <p className="mb-1 font-medium text-foreground">
          {typeof label === "string" && /^\d{4}-\d{2}-\d{2}$/.test(label)
            ? formatDateLabel(label)
            : label}
        </p>
      )}
      <div className="space-y-0.5">
        {payload.map((entry) => (
          <p key={String(entry.dataKey)} className="flex items-center gap-1.5">
            <span
              className="size-2 shrink-0 rounded-full"
              style={{ background: entry.color }}
              aria-hidden="true"
            />
            <span className="text-muted-foreground">{entry.name}</span>
            <span className="font-medium text-foreground">{entry.value}</span>
          </p>
        ))}
      </div>
    </div>
  );
}
