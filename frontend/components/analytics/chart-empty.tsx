import { BarChart3Icon } from "lucide-react";

/** Shown instead of a chart when there isn't enough real data to plot
 * meaningfully — never render an empty or single-point chart as if it
 * were a trend. */
export function ChartEmpty({ message }: { message: string }) {
  return (
    <div className="flex h-48 flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border text-center">
      <BarChart3Icon className="size-5 text-muted-foreground" aria-hidden="true" />
      <p className="max-w-xs px-4 text-sm text-muted-foreground">{message}</p>
    </div>
  );
}
