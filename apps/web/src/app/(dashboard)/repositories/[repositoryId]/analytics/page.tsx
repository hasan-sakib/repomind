"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangleIcon,
  BarChart3Icon,
  FlameIcon,
  GitCommitHorizontalIcon,
  GitPullRequestIcon,
  RefreshCwIcon,
  TimerIcon,
  TriangleAlertIcon,
  UsersIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { ArchitectureHotspotsChart, FileHotspotsChart } from "@/components/analytics/hotspots-view";
import { CommitFrequencyChart } from "@/components/analytics/commit-frequency-chart";
import { ContributorLeaderboard } from "@/components/analytics/contributor-leaderboard";
import { CycleTimePanel } from "@/components/analytics/cycle-time-panel";
import { OpenIssuesPanel } from "@/components/analytics/open-issues-panel";
import { PrThroughputChart } from "@/components/analytics/pr-throughput-chart";
import { RepositoryActivityChart } from "@/components/analytics/repository-activity-chart";
import { TimeRangeToggle } from "@/components/analytics/time-range-toggle";
import { ApiError } from "@/lib/api-client";
import { getAnalyticsSnapshot, triggerAnalyticsSnapshot } from "@/lib/api/analytics";
import { listRepositories } from "@/lib/api/repositories";
import { getRepositoryOverview } from "@/lib/api/repositories";
import { mergeDailyActivity } from "@/lib/analytics-merge";
import { filterByTimeRange, type TimeRange } from "@/lib/analytics-time";
import { useCurrentOrg } from "@/lib/current-org";
import { formatRelativeTime } from "@/lib/format-time";

const ACTIVE_STATUSES = new Set(["queued", "running"]);

function Section({
  title,
  icon: Icon,
  description,
  children,
}: {
  title: string;
  icon: React.ElementType;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-lg border border-border p-4">
      <div className="mb-3 flex items-center gap-2">
        <Icon className="size-4 text-muted-foreground" />
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      </div>
      {description && <p className="mb-3 text-xs text-muted-foreground">{description}</p>}
      {children}
    </section>
  );
}

export default function AnalyticsPage({
  params,
}: {
  params: Promise<{ repositoryId: string }>;
}) {
  const { repositoryId } = use(params);
  const router = useRouter();
  const { currentOrg } = useCurrentOrg();
  const organizationId = currentOrg?.organization.id;
  const queryClient = useQueryClient();
  const [timeRange, setTimeRange] = useState<TimeRange>("30d");
  const [selectedContributor, setSelectedContributor] = useState<string | null>(null);

  const overviewQuery = useQuery({
    queryKey: ["repository-overview", repositoryId],
    queryFn: () => getRepositoryOverview(repositoryId),
  });

  const repositoriesQuery = useQuery({
    queryKey: ["repositories", organizationId],
    queryFn: () => listRepositories(organizationId as string),
    enabled: !!organizationId,
  });

  const snapshotQuery = useQuery({
    queryKey: ["analytics-snapshot", repositoryId],
    queryFn: () => getAnalyticsSnapshot(repositoryId),
    retry: (failureCount, error) =>
      !(error instanceof ApiError && error.code === "analytics_snapshot_not_found") &&
      failureCount < 2,
    refetchInterval: (query) =>
      query.state.data && ACTIVE_STATUSES.has(query.state.data.status) ? 2500 : false,
  });

  const triggerMutation = useMutation({
    mutationFn: (force: boolean) => triggerAnalyticsSnapshot(repositoryId, { force }),
    onSuccess: (snapshot) => {
      queryClient.setQueryData(["analytics-snapshot", repositoryId], snapshot);
      queryClient.invalidateQueries({ queryKey: ["analytics-snapshot", repositoryId] });
    },
  });

  if (overviewQuery.isPending) {
    return (
      <div className="mx-auto max-w-5xl space-y-4 px-4 py-6 sm:px-6">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (overviewQuery.isError) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
        <ErrorState
          title="Couldn't load this repository"
          description="It may have been disconnected, or you may no longer have access."
          onRetry={() => overviewQuery.refetch()}
        />
      </div>
    );
  }

  const { repository } = overviewQuery.data;
  const snapshot = snapshotQuery.data;
  const isActive = snapshot != null && ACTIVE_STATUSES.has(snapshot.status);
  const notSynced = repository.last_synced_at === null;

  const notGenerated =
    snapshotQuery.isError &&
    snapshotQuery.error instanceof ApiError &&
    snapshotQuery.error.code === "analytics_snapshot_not_found";

  const triggerFailedNotSynced =
    triggerMutation.isError &&
    triggerMutation.error instanceof ApiError &&
    triggerMutation.error.code === "repository_not_synced";

  const merged = snapshot
    ? filterByTimeRange(
        mergeDailyActivity(
          snapshot.daily_commit_activity,
          snapshot.daily_pr_issue_activity,
          selectedContributor,
        ),
        timeRange,
      )
    : [];

  const filteredDailyCommits = snapshot
    ? filterByTimeRange(snapshot.daily_commit_activity, timeRange)
    : [];
  const filteredDailyPrIssue = snapshot
    ? filterByTimeRange(snapshot.daily_pr_issue_activity, timeRange)
    : [];

  return (
    <div className="mx-auto max-w-5xl space-y-4 px-4 py-6 sm:px-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold tracking-tight">{repository.full_name}</h1>
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            Engineering activity, throughput, and code hotspots from this repository&apos;s real
            history.
          </p>
          {snapshot?.status === "succeeded" && (
            <p className="mt-1 text-xs text-muted-foreground">
              Generated {formatRelativeTime(snapshot.created_at)} · synced through{" "}
              {formatRelativeTime(snapshot.synced_through)} · {snapshot.commit_sample_size} commits
              sampled, {snapshot.hotspot_commit_sample_size} inspected for hotspots,{" "}
              {snapshot.pr_sample_size} pull requests sampled
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {repositoriesQuery.data && repositoriesQuery.data.length > 1 && (
            <Select
              value={repositoryId}
              onValueChange={(value) => router.push(`/repositories/${value}/analytics`)}
            >
              <SelectTrigger className="h-8 w-48 text-xs">
                <SelectValue>{() => repository.full_name}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {repositoriesQuery.data.map((repo) => (
                  <SelectItem key={repo.id} value={repo.id}>
                    {repo.full_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Button
            size="sm"
            variant={snapshot ? "outline" : "default"}
            disabled={isActive || triggerMutation.isPending || notSynced}
            onClick={() => triggerMutation.mutate(!!snapshot)}
          >
            <BarChart3Icon className="size-3.5" />
            {isActive ? "Generating…" : snapshot ? "Regenerate" : "Generate analytics"}
          </Button>
        </div>
      </div>

      {notSynced && (
        <div className="rounded-lg border border-warning/30 bg-warning/5 px-3 py-2 text-sm text-warning-foreground">
          Sync this repository before generating analytics.{" "}
          <Link href={`/repositories/${repositoryId}`} className="underline">
            Go to overview
          </Link>
          .
        </div>
      )}

      {triggerFailedNotSynced && !notSynced && (
        <div className="rounded-lg border border-warning/30 bg-warning/5 px-3 py-2 text-sm text-warning-foreground">
          Sync this repository before generating analytics.
        </div>
      )}

      {notGenerated && !notSynced && (
        <EmptyState
          icon={BarChart3Icon}
          title="No analytics yet"
          description="Generate an analytics snapshot to see commit activity, PR throughput, review cycle time, and code hotspots — computed from this repository's real history."
          action={
            <Button onClick={() => triggerMutation.mutate(false)} disabled={triggerMutation.isPending}>
              <BarChart3Icon className="size-3.5" />
              Generate analytics
            </Button>
          }
        />
      )}

      {snapshotQuery.isError && !notGenerated && (
        <ErrorState
          description="Couldn't load the analytics snapshot."
          onRetry={() => snapshotQuery.refetch()}
        />
      )}

      {snapshot?.status === "queued" && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-border px-6 py-16 text-center">
          <BarChart3Icon className="size-5 animate-pulse text-brand" />
          <p className="text-sm text-muted-foreground">Waiting to start…</p>
        </div>
      )}

      {snapshot?.status === "running" && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-border px-6 py-16 text-center">
          <RefreshCwIcon className="size-5 animate-spin text-brand" />
          <p className="text-sm text-muted-foreground">
            Sampling commit history and inspecting changed files…
          </p>
        </div>
      )}

      {snapshot?.status === "failed" && (
        <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-6 py-12 text-center">
          <AlertTriangleIcon className="size-5 text-destructive" />
          <div className="space-y-1">
            <p className="text-sm font-medium text-foreground">Generation failed</p>
            <p className="max-w-sm text-sm text-muted-foreground">
              {snapshot.error ?? "An unexpected error occurred."}
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

      {snapshot?.status === "succeeded" && (
        <div className="space-y-4">
          <div className="flex items-center justify-end">
            <TimeRangeToggle value={timeRange} onChange={setTimeRange} />
          </div>

          <Section
            title="Repository Activity"
            icon={BarChart3Icon}
            description="Commits, PRs opened, and issues opened per day."
          >
            <RepositoryActivityChart data={merged} />
          </Section>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Section title="Commit Frequency" icon={GitCommitHorizontalIcon}>
              <CommitFrequencyChart
                dailyCommits={filteredDailyCommits}
                contributors={snapshot.contributor_activity}
                selectedContributor={selectedContributor}
                onSelectContributor={setSelectedContributor}
              />
            </Section>

            <Section
              title="Contributor Activity"
              icon={UsersIcon}
              description="Top contributors by commits and pull requests across the sampled history."
            >
              <ContributorLeaderboard
                contributors={snapshot.contributor_activity}
                selectedContributor={selectedContributor}
                onSelectContributor={setSelectedContributor}
              />
            </Section>
          </div>

          <Section
            title="Pull Request Throughput"
            icon={GitPullRequestIcon}
            description="Pull requests opened, merged, and closed without merging, per day."
          >
            <PrThroughputChart data={filteredDailyPrIssue} />
          </Section>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <Section title="PR Cycle Time" icon={TimerIcon}>
              <CycleTimePanel
                medianHours={snapshot.median_cycle_time_hours}
                samples={snapshot.pr_cycle_time_samples}
              />
            </Section>

            <Section title="Open Issues" icon={TriangleAlertIcon}>
              <OpenIssuesPanel
                openTotal={snapshot.open_issues_total}
                staleIssues={snapshot.stale_issues}
              />
            </Section>
          </div>

          <Section
            title="Code Hotspots"
            icon={FlameIcon}
            description="Files and packages changed most often in the sampled commits — a proxy for where risk and review attention concentrate."
          >
            <div className="space-y-6">
              <div>
                <h3 className="mb-2 text-xs font-medium text-muted-foreground">Files</h3>
                <FileHotspotsChart hotspots={snapshot.file_hotspots} />
              </div>
              <div>
                <h3 className="mb-2 text-xs font-medium text-muted-foreground">Packages</h3>
                <ArchitectureHotspotsChart hotspots={snapshot.architecture_hotspots} />
              </div>
            </div>
          </Section>
        </div>
      )}
    </div>
  );
}
