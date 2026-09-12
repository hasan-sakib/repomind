import { QueryClient } from "@tanstack/react-query";
import { beforeEach, describe, expect, it } from "vitest";

import { applyRealtimeEvent } from "./apply-event";
import { makeIndexingJob, makeRepository } from "@/test/factories";
import type { RealtimeEvent, RepositoryOverview } from "@/lib/types";

function baseEvent(overrides: Partial<RealtimeEvent> = {}): RealtimeEvent {
  return {
    id: "event-1",
    category: "indexing",
    organization_id: "org-1",
    repository_id: "repo-1",
    resource: null,
    data: null,
    title: null,
    level: null,
    at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

let queryClient: QueryClient;

beforeEach(() => {
  queryClient = new QueryClient();
});

describe("applyRealtimeEvent", () => {
  it("does nothing when the event carries no data", () => {
    queryClient.setQueryData(["indexing-jobs", "repo-1"], []);
    applyRealtimeEvent(queryClient, baseEvent({ resource: "indexing_job", data: null }));
    expect(queryClient.getQueryData(["indexing-jobs", "repo-1"])).toEqual([]);
  });

  it("does nothing for an indexing_job event with no repository_id", () => {
    const job = makeIndexingJob({ repository_id: "repo-1" });
    queryClient.setQueryData(["indexing-jobs", "repo-1"], []);
    applyRealtimeEvent(
      queryClient,
      baseEvent({ resource: "indexing_job", repository_id: null, data: job as never }),
    );
    expect(queryClient.getQueryData(["indexing-jobs", "repo-1"])).toEqual([]);
  });

  it("prepends a new indexing job and de-dupes an existing one by id", () => {
    const existing = makeIndexingJob({ id: "job-1", repository_id: "repo-1" });
    queryClient.setQueryData(["indexing-jobs", "repo-1"], [existing]);

    const updated = { ...existing, status: "running" };
    applyRealtimeEvent(
      queryClient,
      baseEvent({ resource: "indexing_job", repository_id: "repo-1", data: updated as never }),
    );

    const cached = queryClient.getQueryData(["indexing-jobs", "repo-1"]) as unknown[];
    expect(cached).toHaveLength(1);
    expect(cached[0]).toMatchObject({ id: "job-1", status: "running" });
  });

  it("does not create a cache entry that was never fetched (nothing to patch)", () => {
    const job = makeIndexingJob({ repository_id: "repo-1" });
    applyRealtimeEvent(
      queryClient,
      baseEvent({ resource: "indexing_job", repository_id: "repo-1", data: job as never }),
    );
    expect(queryClient.getQueryData(["indexing-jobs", "repo-1"])).toBeUndefined();
  });

  it("patches a cached repository overview's repository field in place", () => {
    const repo = makeRepository({ id: "repo-1", status: "ready" });
    const overview: RepositoryOverview = {
      repository: { ...repo, status: "syncing" },
      recent_commits: [],
      open_pull_requests: [],
      open_issues: [],
    };
    queryClient.setQueryData(["repository-overview", "repo-1"], overview);

    applyRealtimeEvent(queryClient, baseEvent({ resource: "repository", data: repo as never }));

    const cached = queryClient.getQueryData<RepositoryOverview>(["repository-overview", "repo-1"]);
    expect(cached?.repository.status).toBe("ready");
    expect(cached?.recent_commits).toEqual([]);
  });

  it("updates a matching repository inside any cached repositories list", () => {
    const repoA = makeRepository({ id: "repo-a", name: "a", status: "syncing" });
    const repoB = makeRepository({ id: "repo-b", name: "b", status: "ready" });
    queryClient.setQueryData(["repositories", "org-1"], [repoA, repoB]);

    const updatedA = { ...repoA, status: "ready" };
    applyRealtimeEvent(
      queryClient,
      baseEvent({ resource: "repository", data: updatedA as never }),
    );

    const cached = queryClient.getQueryData(["repositories", "org-1"]) as typeof repoA[];
    expect(cached.find((r) => r.id === "repo-a")?.status).toBe("ready");
    expect(cached.find((r) => r.id === "repo-b")?.status).toBe("ready");
  });

  it("writes a pull_request_analysis event keyed by repository and PR number", () => {
    const analysis = { pull_request_number: 42, status: "succeeded" };
    applyRealtimeEvent(
      queryClient,
      baseEvent({
        resource: "pull_request_analysis",
        repository_id: "repo-1",
        data: analysis as never,
      }),
    );
    expect(queryClient.getQueryData(["pull-request-analysis", "repo-1", 42])).toEqual(analysis);
  });

  it("is a silent no-op for an event resource it doesn't recognize", () => {
    expect(() =>
      applyRealtimeEvent(
        queryClient,
        baseEvent({ resource: "webhook_event", data: { anything: true } }),
      ),
    ).not.toThrow();
  });
});
