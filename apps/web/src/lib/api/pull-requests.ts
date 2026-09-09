import { apiFetch } from "@/lib/api-client";
import type { PullRequest, PullRequestAnalysis } from "@/lib/types";

export function getPullRequest(repositoryId: string, number: number): Promise<PullRequest> {
  return apiFetch(`/api/v1/repositories/${repositoryId}/pull-requests/${number}`);
}

export function getPullRequestAnalysis(
  repositoryId: string,
  number: number,
): Promise<PullRequestAnalysis> {
  return apiFetch(`/api/v1/repositories/${repositoryId}/pull-requests/${number}/analysis`);
}

export function triggerPullRequestAnalysis(
  repositoryId: string,
  number: number,
  options: { force?: boolean } = {},
): Promise<PullRequestAnalysis> {
  const query = options.force ? "?force=true" : "";
  return apiFetch(
    `/api/v1/repositories/${repositoryId}/pull-requests/${number}/analysis${query}`,
    { method: "POST" },
  );
}
