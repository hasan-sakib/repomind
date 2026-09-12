import type { QueryClient } from "@tanstack/react-query";

import type {
  AnalyticsSnapshot,
  IndexingJob,
  OnboardingGuide,
  PullRequestAnalysis,
  RealtimeEvent,
  Repository,
  RepositoryOverview,
} from "@/lib/types";

/**
 * Writes a state-sync event's payload straight into the matching React
 * Query cache entry instead of invalidating and refetching — this is
 * what lets the frontend update without the user ever seeing a loading
 * flash for something that already pushed its fresh state over the
 * wire. Notification-category events never reach here — the caller
 * (lib/realtime-context.tsx) handles those itself. A resource this
 * function doesn't recognize, or an event for a page that was never
 * fetched (so there's nothing cached to touch), is a silent no-op by
 * design: setQueryData on a query that isn't in the cache does nothing.
 */
export function applyRealtimeEvent(queryClient: QueryClient, event: RealtimeEvent): void {
  if (!event.data) return;

  switch (event.resource) {
    case "indexing_job": {
      if (!event.repository_id) return;
      const job = event.data as unknown as IndexingJob;
      queryClient.setQueryData<IndexingJob[]>(["indexing-jobs", event.repository_id], (old) =>
        old ? [job, ...old.filter((existing) => existing.id !== job.id)] : old,
      );
      break;
    }

    case "repository": {
      const repo = event.data as unknown as Repository;
      queryClient.setQueryData<RepositoryOverview>(["repository-overview", repo.id], (old) =>
        old ? { ...old, repository: repo } : old,
      );
      queryClient.setQueriesData<Repository[]>({ queryKey: ["repositories"] }, (old) =>
        old ? old.map((existing) => (existing.id === repo.id ? repo : existing)) : old,
      );
      break;
    }

    case "pull_request_analysis": {
      if (!event.repository_id) return;
      const analysis = event.data as unknown as PullRequestAnalysis & {
        pull_request_number: number;
      };
      queryClient.setQueryData(
        ["pull-request-analysis", event.repository_id, analysis.pull_request_number],
        analysis,
      );
      break;
    }

    case "onboarding_guide": {
      if (!event.repository_id) return;
      queryClient.setQueryData(
        ["onboarding-guide", event.repository_id],
        event.data as unknown as OnboardingGuide,
      );
      break;
    }

    case "analytics_snapshot": {
      if (!event.repository_id) return;
      queryClient.setQueryData(
        ["analytics-snapshot", event.repository_id],
        event.data as unknown as AnalyticsSnapshot,
      );
      break;
    }

    default:
      // "webhook_event" (and anything else) has no dedicated page cache
      // to patch — it's informational, surfaced only via the paired
      // notification-category event.
      break;
  }
}
