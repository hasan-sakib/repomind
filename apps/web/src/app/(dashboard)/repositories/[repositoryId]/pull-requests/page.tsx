"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { GitPullRequestIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { getRepositoryOverview, listPullRequests } from "@/lib/api/repositories";
import { formatRelativeTime } from "@/lib/format-time";
import { cn } from "cn";

type StateFilter = "open" | "closed" | undefined;

const FILTERS: { label: string; value: StateFilter }[] = [
  { label: "Open", value: "open" },
  { label: "Closed", value: "closed" },
  { label: "All", value: undefined },
];

export default function PullRequestsPage({
  params,
}: {
  params: Promise<{ repositoryId: string }>;
}) {
  const { repositoryId } = use(params);
  const [state, setState] = useState<StateFilter>("open");

  const overviewQuery = useQuery({
    queryKey: ["repository-overview", repositoryId],
    queryFn: () => getRepositoryOverview(repositoryId),
  });

  const pullRequestsQuery = useQuery({
    queryKey: ["pull-requests", repositoryId, state],
    queryFn: () => listPullRequests(repositoryId, state),
  });

  return (
    <div className="mx-auto max-w-4xl space-y-4 px-4 py-6 sm:px-6">
      <div>
        <h1 className="truncate text-lg font-semibold tracking-tight">
          {overviewQuery.data?.repository.full_name ?? "Pull requests"}
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          AI-powered risk analysis for this repository&apos;s pull requests.
        </p>
      </div>

      <div className="flex gap-1.5">
        {FILTERS.map((filter) => (
          <button
            key={filter.label}
            type="button"
            onClick={() => setState(filter.value)}
            className={cn(
              "rounded-full border px-2.5 py-1 text-xs font-medium transition-colors",
              state === filter.value
                ? "border-brand bg-brand/10 text-brand"
                : "border-border text-muted-foreground hover:text-foreground",
            )}
          >
            {filter.label}
          </button>
        ))}
      </div>

      {pullRequestsQuery.isPending && (
        <div className="space-y-2 rounded-lg border border-border p-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      )}

      {pullRequestsQuery.isError && (
        <ErrorState
          description="Couldn't load pull requests."
          onRetry={() => pullRequestsQuery.refetch()}
        />
      )}

      {pullRequestsQuery.data && pullRequestsQuery.data.length === 0 && (
        <EmptyState
          icon={GitPullRequestIcon}
          title="No pull requests"
          description="No pull requests match this filter yet."
        />
      )}

      {pullRequestsQuery.data && pullRequestsQuery.data.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Pull request</TableHead>
                <TableHead>Author</TableHead>
                <TableHead>Updated</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pullRequestsQuery.data.map((pr) => (
                <TableRow key={pr.number}>
                  <TableCell className="font-medium">
                    <Link
                      href={`/repositories/${repositoryId}/pull-requests/${pr.number}`}
                      className="flex items-center gap-2 text-foreground hover:text-brand hover:underline"
                    >
                      <span className="text-muted-foreground">#{pr.number}</span>
                      <span className="line-clamp-1">{pr.title}</span>
                      {pr.merged_at ? (
                        <Badge variant="brand" className="shrink-0 text-[10px]">
                          Merged
                        </Badge>
                      ) : pr.state === "closed" ? (
                        <Badge variant="outline" className="shrink-0 text-[10px]">
                          Closed
                        </Badge>
                      ) : (
                        <Badge variant="success" className="shrink-0 text-[10px]">
                          Open
                        </Badge>
                      )}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {pr.author_login ?? "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatRelativeTime(pr.github_updated_at)}
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
