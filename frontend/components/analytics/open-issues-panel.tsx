import { ExternalLinkIcon } from "lucide-react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { StaleIssue } from "@/lib/types";
import { ChartEmpty } from "./chart-empty";

export function OpenIssuesPanel({
  openTotal,
  staleIssues,
}: {
  openTotal: number;
  staleIssues: StaleIssue[];
}) {
  if (openTotal === 0) {
    return <ChartEmpty message="No open issues in the sampled history." />;
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-muted-foreground">
        Open issues: <span className="font-medium text-foreground">{openTotal}</span>
        {staleIssues.length > 0 && (
          <>
            {" "}
            · <span className="font-medium text-foreground">{staleIssues.length}</span> older
            than the staleness threshold
          </>
        )}
      </p>
      {staleIssues.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          None of the open issues are old enough to flag as stale.
        </p>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Issue</TableHead>
                <TableHead className="text-right">Age</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {staleIssues.map((issue) => (
                <TableRow key={issue.number}>
                  <TableCell className="max-w-xs">
                    <a
                      href={issue.html_url}
                      target="_blank"
                      rel="noreferrer"
                      className="flex items-center gap-1.5 truncate text-foreground hover:text-brand hover:underline"
                    >
                      <span className="shrink-0 text-muted-foreground">#{issue.number}</span>
                      <span className="truncate">{issue.title}</span>
                      <ExternalLinkIcon className="size-3 shrink-0 text-muted-foreground" />
                    </a>
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    {issue.age_days}d
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
