"use client";

import { use } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangleIcon,
  ClockIcon,
  ExternalLinkIcon,
  RefreshCwIcon,
  ShieldAlertIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { AnalysisPanel } from "@/components/pull-requests/analysis-panel";
import { AnalysisStatusBadge } from "@/components/pull-requests/analysis-status-badge";
import { ApiError } from "@/lib/api-client";
import {
  getPullRequest,
  getPullRequestAnalysis,
  triggerPullRequestAnalysis,
} from "@/lib/api/pull-requests";
import { getRepositoryOverview } from "@/lib/api/repositories";
import { formatRelativeTime } from "@/lib/format-time";
import { useRealtime } from "@/lib/realtime-context";

const ACTIVE_STATUSES = new Set(["queued", "running"]);

export default function PullRequestDetailPage({
  params,
}: {
  params: Promise<{ repositoryId: string; number: string }>;
}) {
  const { repositoryId, number: numberParam } = use(params);
  const number = Number(numberParam);
  const queryClient = useQueryClient();
  const { status: connectionStatus } = useRealtime();

  const overviewQuery = useQuery({
    queryKey: ["repository-overview", repositoryId],
    queryFn: () => getRepositoryOverview(repositoryId),
  });

  const pullRequestQuery = useQuery({
    queryKey: ["pull-request", repositoryId, number],
    queryFn: () => getPullRequest(repositoryId, number),
  });

  const analysisQuery = useQuery({
    queryKey: ["pull-request-analysis", repositoryId, number],
    queryFn: () => getPullRequestAnalysis(repositoryId, number),
    retry: (failureCount, error) =>
      !(error instanceof ApiError && error.code === "pull_request_analysis_not_found") &&
      failureCount < 2,
    // The real-time connection already pushes analysis-status updates
    // straight into this cache — polling is purely a fallback for when
    // it isn't connected.
    refetchInterval: (query) =>
      connectionStatus !== "open" &&
      query.state.data &&
      ACTIVE_STATUSES.has(query.state.data.status)
        ? 2000
        : false,
  });

  const triggerMutation = useMutation({
    mutationFn: (force: boolean) => triggerPullRequestAnalysis(repositoryId, number, { force }),
    onSuccess: (analysis) => {
      queryClient.setQueryData(["pull-request-analysis", repositoryId, number], analysis);
      queryClient.invalidateQueries({ queryKey: ["pull-request-analysis", repositoryId, number] });
    },
  });

  const analysisNotFound =
    analysisQuery.isError &&
    analysisQuery.error instanceof ApiError &&
    analysisQuery.error.code === "pull_request_analysis_not_found";

  if (overviewQuery.isPending || pullRequestQuery.isPending) {
    return (
      <div className="mx-auto max-w-4xl space-y-4 px-4 py-6 sm:px-6">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (overviewQuery.isError || pullRequestQuery.isError) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
        <ErrorState
          title="Couldn't load this pull request"
          description="It may have been disconnected, or you may no longer have access."
          onRetry={() => {
            overviewQuery.refetch();
            pullRequestQuery.refetch();
          }}
        />
      </div>
    );
  }

  const { repository } = overviewQuery.data;
  const pr = pullRequestQuery.data;
  const analysis = analysisQuery.data;
  const isActive = analysis != null && ACTIVE_STATUSES.has(analysis.status);
  const isStale = analysis != null && analysis.status === "succeeded" && analysis.head_sha !== pr.head_sha;

  return (
    <div className="mx-auto max-w-4xl space-y-4 px-4 py-6 sm:px-6">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="truncate text-lg font-semibold tracking-tight">
              #{pr.number} {pr.title}
            </h1>
            <a
              href={pr.html_url}
              target="_blank"
              rel="noreferrer"
              className="shrink-0 text-muted-foreground hover:text-foreground"
              aria-label="Open on GitHub"
            >
              <ExternalLinkIcon className="size-3.5" />
            </a>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {pr.author_login ?? "unknown"} opened this{" "}
            {formatRelativeTime(pr.github_created_at)}
            {pr.merged_at
              ? ` · merged ${formatRelativeTime(pr.merged_at)}`
              : pr.state === "closed"
                ? ` · closed ${formatRelativeTime(pr.closed_at)}`
                : ""}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {analysis && <AnalysisStatusBadge status={analysis.status} />}
          <Button
            size="sm"
            variant={analysis ? "outline" : "default"}
            disabled={isActive || triggerMutation.isPending}
            onClick={() => triggerMutation.mutate(!!analysis)}
          >
            <RefreshCwIcon className={isActive ? "size-3.5 animate-spin" : "size-3.5"} />
            {isActive
              ? "Analyzing…"
              : analysis
                ? isStale
                  ? "Re-analyze (new commits)"
                  : "Re-analyze"
                : "Analyze this PR"}
          </Button>
        </div>
      </div>

      {triggerMutation.isError && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          Couldn&apos;t start analysis: {triggerMutation.error.message}
        </div>
      )}

      {isStale && !isActive && (
        <div className="rounded-lg border border-warning/30 bg-warning/5 px-3 py-2 text-sm text-warning-foreground">
          New commits were pushed since this analysis ran — it may be out of date.
        </div>
      )}

      {analysisQuery.isPending && (
        <div className="space-y-2 rounded-lg border border-border p-4">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      )}

      {analysisNotFound && (
        <EmptyState
          icon={ShieldAlertIcon}
          title="Not analyzed yet"
          description="Run RepoMind's AI analysis to see risk level, affected components, and recommended tests for this pull request."
          action={
            <Button onClick={() => triggerMutation.mutate(false)} disabled={triggerMutation.isPending}>
              <RefreshCwIcon className="size-3.5" />
              Analyze this PR
            </Button>
          }
        />
      )}

      {analysisQuery.isError && !analysisNotFound && (
        <ErrorState
          description="Couldn't load the analysis."
          onRetry={() => analysisQuery.refetch()}
        />
      )}

      {analysis?.status === "queued" && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-border px-6 py-16 text-center">
          <ClockIcon className="size-5 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Waiting to start…</p>
        </div>
      )}

      {analysis?.status === "running" && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-border px-6 py-16 text-center">
          <RefreshCwIcon className="size-5 animate-spin text-brand" />
          <p className="text-sm text-muted-foreground">
            Analyzing changed files, dependencies, and tests…
          </p>
        </div>
      )}

      {analysis?.status === "failed" && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-6 py-12 text-center">
          <AlertTriangleIcon className="size-5 text-destructive" />
          <div className="space-y-1">
            <p className="text-sm font-medium text-foreground">Analysis failed</p>
            <p className="max-w-sm text-sm text-muted-foreground">
              {analysis.error ?? "An unexpected error occurred."}
            </p>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => triggerMutation.mutate(true)}
            disabled={triggerMutation.isPending}
          >
            <RefreshCwIcon className="size-3.5" />
            Try again
          </Button>
        </div>
      )}

      {analysis?.status === "succeeded" && (
        <AnalysisPanel analysis={analysis} repository={repository} />
      )}
    </div>
  );
}
