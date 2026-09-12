"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  BarChart3Icon,
  BookOpenIcon,
  ExternalLinkIcon,
  GitBranchIcon,
  GitCommitHorizontalIcon,
  GitPullRequestIcon,
  CircleDotIcon,
  DatabaseZapIcon,
  MessageSquareIcon,
  NetworkIcon,
  RefreshCwIcon,
  StarIcon,
  GitForkIcon,
  SettingsIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/error-state";
import { FadeIn } from "@/components/fade-in";
import { RepositoryStatusBadge } from "@/components/repository/status-badge";
import { getRepositoryOverview, syncRepositoryNow } from "@/lib/api/repositories";
import { formatRelativeTime } from "@/lib/format-time";
import { useRealtime } from "@/lib/realtime-context";

export default function RepositoryOverviewPage({
  params,
}: {
  params: Promise<{ repositoryId: string }>;
}) {
  const { repositoryId } = use(params);
  const queryClient = useQueryClient();
  const [justTriggeredSync, setJustTriggeredSync] = useState(false);
  const { status: connectionStatus } = useRealtime();

  const overviewQuery = useQuery({
    queryKey: ["repository-overview", repositoryId],
    queryFn: () => getRepositoryOverview(repositoryId),
    // The real-time connection already pushes sync-status updates
    // straight into this cache — polling is purely a fallback for when
    // it isn't connected.
    refetchInterval: (query) =>
      connectionStatus !== "open" && query.state.data?.repository.status === "syncing"
        ? 2000
        : false,
  });

  const syncMutation = useMutation({
    mutationFn: () => syncRepositoryNow(repositoryId),
    onSuccess: () => {
      setJustTriggeredSync(true);
      queryClient.invalidateQueries({ queryKey: ["repository-overview", repositoryId] });
    },
  });

  if (overviewQuery.isPending) {
    return (
      <div className="mx-auto max-w-4xl space-y-4 px-4 py-6 sm:px-6">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-5 w-full max-w-md" />
        <div className="grid gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-40 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (overviewQuery.isError) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
        <ErrorState
          title="Couldn't load this repository"
          description="It may have been disconnected, or you may no longer have access."
          onRetry={() => overviewQuery.refetch()}
        />
      </div>
    );
  }

  const { repository, recent_commits, open_pull_requests, open_issues } = overviewQuery.data;
  const isSyncing = repository.status === "syncing";

  return (
    <FadeIn className="mx-auto max-w-4xl space-y-4 px-4 py-6 sm:px-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="truncate text-lg font-semibold tracking-tight">
              {repository.full_name}
            </h1>
            <RepositoryStatusBadge status={repository.status} />
            <a
              href={repository.html_url}
              target="_blank"
              rel="noreferrer"
              className="text-muted-foreground hover:text-foreground"
              aria-label="Open on GitHub"
            >
              <ExternalLinkIcon className="size-3.5" />
            </a>
          </div>
          {repository.description && (
            <p className="mt-1 text-sm text-muted-foreground">{repository.description}</p>
          )}
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:shrink-0">
          <Button size="sm" render={<Link href={`/repositories/${repositoryId}/chat`} />}>
            <MessageSquareIcon className="size-3.5" />
            Chat
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={isSyncing || syncMutation.isPending}
            onClick={() => syncMutation.mutate()}
          >
            <RefreshCwIcon className={isSyncing ? "size-3.5 animate-spin" : "size-3.5"} />
            {isSyncing ? "Syncing…" : "Sync now"}
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            render={<Link href={`/repositories/${repositoryId}/indexing`} />}
            aria-label="Indexing"
          >
            <DatabaseZapIcon className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            render={<Link href={`/repositories/${repositoryId}/architecture`} />}
            aria-label="Architecture"
          >
            <NetworkIcon className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            render={<Link href={`/repositories/${repositoryId}/pull-requests`} />}
            aria-label="Pull requests"
          >
            <GitPullRequestIcon className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            render={<Link href={`/repositories/${repositoryId}/onboarding`} />}
            aria-label="Onboarding"
          >
            <BookOpenIcon className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            render={<Link href={`/repositories/${repositoryId}/analytics`} />}
            aria-label="Analytics"
          >
            <BarChart3Icon className="size-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            render={<Link href={`/repositories/${repositoryId}/settings`} />}
            aria-label="Repository settings"
          >
            <SettingsIcon className="size-4" />
          </Button>
        </div>
      </div>

      {repository.status === "error" && repository.sync_error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          Last sync failed: {repository.sync_error}
        </div>
      )}
      {justTriggeredSync && syncMutation.isSuccess && !isSyncing && (
        <div className="rounded-lg border border-success/30 bg-success/5 px-3 py-2 text-sm text-success">
          Sync complete.
        </div>
      )}

      {/* Compact metadata strip — not cards. */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg border border-border px-3 py-2 text-sm text-muted-foreground">
        {repository.language && (
          <span className="flex items-center gap-1">
            <span className="size-2 rounded-full bg-brand" />
            {repository.language}
          </span>
        )}
        <span className="flex items-center gap-1">
          <StarIcon className="size-3.5" />
          {repository.stargazers_count}
        </span>
        <span className="flex items-center gap-1">
          <GitForkIcon className="size-3.5" />
          {repository.forks_count}
        </span>
        <span className="flex items-center gap-1">
          <GitBranchIcon className="size-3.5" />
          {repository.default_branch}
        </span>
        <span className="ml-auto">Last synced {formatRelativeTime(repository.last_synced_at)}</span>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <OverviewSection
          icon={GitCommitHorizontalIcon}
          title="Recent commits"
          emptyLabel="No commits synced yet"
          count={recent_commits.length}
        >
          {recent_commits.map((commit) => (
            <li key={commit.sha} className="px-3 py-2 text-sm">
              <a
                href={commit.html_url}
                target="_blank"
                rel="noreferrer"
                className="line-clamp-1 font-medium text-foreground hover:text-brand hover:underline"
              >
                {commit.message.split("\n")[0]}
              </a>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {commit.author_login ?? commit.author_name ?? "unknown"} ·{" "}
                {formatRelativeTime(commit.authored_at)}
              </p>
            </li>
          ))}
        </OverviewSection>

        <OverviewSection
          icon={GitPullRequestIcon}
          title="Open pull requests"
          emptyLabel="No open pull requests"
          count={open_pull_requests.length}
        >
          {open_pull_requests.map((pr) => (
            <li key={pr.number} className="px-3 py-2 text-sm">
              <Link
                href={`/repositories/${repositoryId}/pull-requests/${pr.number}`}
                className="line-clamp-1 font-medium text-foreground hover:text-brand hover:underline"
              >
                #{pr.number} {pr.title}
              </Link>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {pr.author_login ?? "unknown"} · {formatRelativeTime(pr.github_updated_at)}
              </p>
            </li>
          ))}
        </OverviewSection>

        <OverviewSection
          icon={CircleDotIcon}
          title="Open issues"
          emptyLabel="No open issues"
          count={open_issues.length}
        >
          {open_issues.map((issue) => (
            <li key={issue.number} className="px-3 py-2 text-sm">
              <a
                href={issue.html_url}
                target="_blank"
                rel="noreferrer"
                className="line-clamp-1 font-medium text-foreground hover:text-brand hover:underline"
              >
                #{issue.number} {issue.title}
              </a>
              <p className="mt-0.5 text-xs text-muted-foreground">
                {issue.author_login ?? "unknown"} · {formatRelativeTime(issue.github_updated_at)}
              </p>
            </li>
          ))}
        </OverviewSection>
      </div>
    </FadeIn>
  );
}

function OverviewSection({
  icon: Icon,
  title,
  count,
  emptyLabel,
  children,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  count: number;
  emptyLabel: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border">
      <div className="flex items-center gap-1.5 border-b border-border px-3 py-2 text-xs font-medium text-muted-foreground">
        <Icon className="size-3.5" />
        {title}
        <span className="ml-auto">{count}</span>
      </div>
      {count === 0 ? (
        <p className="px-3 py-6 text-center text-xs text-muted-foreground">{emptyLabel}</p>
      ) : (
        <ul className="max-h-72 divide-y divide-border overflow-y-auto">{children}</ul>
      )}
    </div>
  );
}
