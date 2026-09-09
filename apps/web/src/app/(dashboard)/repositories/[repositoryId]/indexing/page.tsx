"use client";

import { use } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangleIcon,
  CircleCheckIcon,
  DatabaseZapIcon,
  FileCodeIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/error-state";
import { IndexingStatusBadge } from "@/components/repositories/indexing-status-badge";
import { listIndexingJobs, triggerIndexing } from "@/lib/api/indexing";
import { getRepositoryOverview } from "@/lib/api/repositories";
import { formatRelativeTime } from "@/lib/format-time";
import { useRealtime } from "@/lib/realtime-context";
import {
  INDEXING_STAGE_LABELS,
  INDEXING_STAGE_ORDER,
  INDEXING_TRIGGER_LABELS,
  type IndexingJob,
} from "@/lib/types";

const ACTIVE_STATUSES = new Set(["queued", "running"]);

export default function RepositoryIndexingPage({
  params,
}: {
  params: Promise<{ repositoryId: string }>;
}) {
  const { repositoryId } = use(params);
  const queryClient = useQueryClient();
  const { status: connectionStatus } = useRealtime();

  const overviewQuery = useQuery({
    queryKey: ["repository-overview", repositoryId],
    queryFn: () => getRepositoryOverview(repositoryId),
  });

  const jobsQuery = useQuery({
    queryKey: ["indexing-jobs", repositoryId],
    queryFn: () => listIndexingJobs(repositoryId),
    // The real-time connection already pushes progress updates straight
    // into this cache (lib/realtime/apply-event.ts) — polling is purely
    // a fallback for when it isn't connected.
    refetchInterval: (query) => {
      if (connectionStatus === "open") return false;
      const latest = query.state.data?.[0];
      return latest && ACTIVE_STATUSES.has(latest.status) ? 2000 : false;
    },
  });

  const triggerMutation = useMutation({
    mutationFn: () => triggerIndexing(repositoryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["indexing-jobs", repositoryId] });
    },
  });

  if (overviewQuery.isPending || jobsQuery.isPending) {
    return (
      <div className="mx-auto max-w-4xl space-y-4 px-4 py-6 sm:px-6">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (overviewQuery.isError || jobsQuery.isError) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
        <ErrorState
          title="Couldn't load indexing status"
          description="It may have been disconnected, or you may no longer have access."
          onRetry={() => {
            overviewQuery.refetch();
            jobsQuery.refetch();
          }}
        />
      </div>
    );
  }

  const { repository } = overviewQuery.data;
  const jobs = jobsQuery.data;
  const [latestJob, ...previousJobs] = jobs;
  const isActive = latestJob !== undefined && ACTIVE_STATUSES.has(latestJob.status);

  return (
    <div className="mx-auto max-w-4xl space-y-4 px-4 py-6 sm:px-6">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h1 className="truncate text-lg font-semibold tracking-tight">{repository.full_name}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Indexing builds the searchable code database — files, symbols, and embeddings.
          </p>
        </div>
        <Button
          size="sm"
          disabled={isActive || triggerMutation.isPending}
          onClick={() => triggerMutation.mutate()}
        >
          <DatabaseZapIcon className="size-3.5" />
          {isActive ? "Indexing…" : "Index now"}
        </Button>
      </div>

      {triggerMutation.isError && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          Couldn&apos;t start indexing: {triggerMutation.error.message}
        </div>
      )}

      {latestJob ? (
        <IndexingJobPanel job={latestJob} />
      ) : (
        <div className="flex flex-col items-center justify-center gap-3 rounded-lg border border-border px-6 py-16 text-center">
          <div className="flex size-10 items-center justify-center rounded-full bg-muted">
            <DatabaseZapIcon className="size-5 text-muted-foreground" aria-hidden="true" />
          </div>
          <div className="space-y-1">
            <p className="text-sm font-medium text-foreground">Not indexed yet</p>
            <p className="max-w-sm text-sm text-muted-foreground">
              Index this repository to make its code searchable.
            </p>
          </div>
        </div>
      )}

      {previousJobs.length > 0 && (
        <div className="rounded-lg border border-border">
          <div className="flex items-center gap-1.5 border-b border-border px-3 py-2 text-xs font-medium text-muted-foreground">
            <FileCodeIcon className="size-3.5" />
            Previous runs
          </div>
          <ul className="divide-y divide-border">
            {previousJobs.map((job) => (
              <li key={job.id} className="flex items-center justify-between gap-3 px-3 py-2 text-sm">
                <div className="flex min-w-0 items-center gap-2">
                  <IndexingStatusBadge status={job.status} />
                  <span className="truncate text-xs text-muted-foreground">
                    {INDEXING_TRIGGER_LABELS[job.trigger]} · {job.commit_sha.slice(0, 7)}
                  </span>
                </div>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {formatRelativeTime(job.created_at)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function IndexingJobPanel({ job }: { job: IndexingJob }) {
  const totalKnown = job.files_discovered;
  const done = job.files_processed + job.files_skipped;
  const fileProgress = totalKnown > 0 ? (done / totalKnown) * 100 : 0;
  const embeddingProgress = job.chunks_created > 0 ? (job.embeddings_generated / job.chunks_created) * 100 : 0;

  return (
    <div className="space-y-4 rounded-lg border border-border p-4">
      <div className="flex flex-wrap items-center gap-2">
        <IndexingStatusBadge status={job.status} />
        <span className="text-xs text-muted-foreground">
          {INDEXING_TRIGGER_LABELS[job.trigger]} · commit {job.commit_sha.slice(0, 7)}
        </span>
        <span className="ml-auto text-xs text-muted-foreground">
          {job.finished_at
            ? `Finished ${formatRelativeTime(job.finished_at)}`
            : job.started_at
              ? `Started ${formatRelativeTime(job.started_at)}`
              : "Queued"}
        </span>
      </div>

      {/* Stage track — current position in the real pipeline, not a fabricated percentage. */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium text-foreground">
            {job.current_stage ? INDEXING_STAGE_LABELS[job.current_stage] : "Waiting to start"}
          </span>
          {totalKnown > 0 && (
            <span className="text-muted-foreground">
              {done} / {totalKnown} files
            </span>
          )}
        </div>
        <Progress value={fileProgress} />
        <div className="flex justify-between">
          {INDEXING_STAGE_ORDER.map((stage) => {
            const currentIndex = job.current_stage ? INDEXING_STAGE_ORDER.indexOf(job.current_stage) : -1;
            const stageIndex = INDEXING_STAGE_ORDER.indexOf(stage);
            const reached = currentIndex >= stageIndex;
            return (
              <span
                key={stage}
                className={
                  reached
                    ? "size-1.5 rounded-full bg-brand"
                    : "size-1.5 rounded-full bg-muted"
                }
                title={INDEXING_STAGE_LABELS[stage]}
              />
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Files discovered" value={job.files_discovered} />
        <Stat label="Files processed" value={job.files_processed} />
        <Stat label="Symbols extracted" value={job.symbols_extracted} />
        <Stat label="Chunks created" value={job.chunks_created} />
      </div>

      {job.chunks_created > 0 && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Embeddings generated</span>
            <span className="text-muted-foreground">
              {job.embeddings_generated} / {job.chunks_created}
            </span>
          </div>
          <Progress value={embeddingProgress} />
        </div>
      )}

      {job.status === "succeeded" && (
        <div className="flex items-center gap-1.5 text-sm text-success">
          <CircleCheckIcon className="size-3.5" />
          Indexed successfully.
        </div>
      )}

      {job.error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {job.error}
        </div>
      )}

      {job.errors.length > 0 && (
        <div className="rounded-lg border border-warning/30">
          <div className="flex items-center gap-1.5 border-b border-warning/30 px-3 py-2 text-xs font-medium text-warning-foreground">
            <AlertTriangleIcon className="size-3.5" />
            {job.errors.length} file{job.errors.length === 1 ? "" : "s"} had errors
          </div>
          <ul className="max-h-48 divide-y divide-border overflow-y-auto">
            {job.errors.map((err) => (
              <li key={err.id} className="px-3 py-2 text-xs">
                <p className="font-medium text-foreground">{err.file_path ?? "(no file)"}</p>
                <p className="mt-0.5 text-muted-foreground">{err.message}</p>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border px-3 py-2">
      <p className="text-lg font-semibold tabular-nums tracking-tight">{value.toLocaleString()}</p>
      <p className="text-xs text-muted-foreground">{label}</p>
    </div>
  );
}
