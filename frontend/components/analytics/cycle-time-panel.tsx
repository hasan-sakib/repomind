import { ExternalLinkIcon } from "lucide-react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { PRCycleTimeSample } from "@/lib/types";
import { ChartEmpty } from "./chart-empty";

function formatHours(hours: number): string {
  if (hours < 24) return `${hours.toFixed(1)}h`;
  return `${(hours / 24).toFixed(1)}d`;
}

export function CycleTimePanel({
  medianHours,
  samples,
}: {
  medianHours: number | null;
  samples: PRCycleTimeSample[];
}) {
  if (medianHours === null || samples.length === 0) {
    return (
      <ChartEmpty message="No merged or closed pull requests in the sampled history yet." />
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Median time from open to merge/close:{" "}
        <span className="font-medium text-foreground">{formatHours(medianHours)}</span>
      </p>
      <div className="overflow-x-auto rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Pull request</TableHead>
              <TableHead className="text-right">Cycle time</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {samples.map((sample) => (
              <TableRow key={sample.number}>
                <TableCell className="max-w-xs">
                  <a
                    href={sample.html_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 truncate text-foreground hover:text-brand hover:underline"
                  >
                    <span className="shrink-0 text-muted-foreground">#{sample.number}</span>
                    <span className="truncate">{sample.title}</span>
                    <ExternalLinkIcon className="size-3 shrink-0 text-muted-foreground" />
                  </a>
                </TableCell>
                <TableCell className="text-right text-muted-foreground">
                  {formatHours(sample.hours)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <p className="text-xs text-muted-foreground">
        Measured from PR open to merge/close — not time to first review (this repository&apos;s
        synced data doesn&apos;t track individual reviews).
      </p>
    </div>
  );
}
