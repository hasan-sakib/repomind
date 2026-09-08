import { apiFetch } from "@/lib/api-client";
import type { IndexingJob, TriggerIndexingResponse } from "@/lib/types";

export function triggerIndexing(repositoryId: string): Promise<TriggerIndexingResponse> {
  return apiFetch(`/api/v1/repositories/${repositoryId}/indexing-jobs`, { method: "POST" });
}

export function listIndexingJobs(repositoryId: string): Promise<IndexingJob[]> {
  return apiFetch(`/api/v1/repositories/${repositoryId}/indexing-jobs`);
}

export function getIndexingJob(repositoryId: string, jobId: string): Promise<IndexingJob> {
  return apiFetch(`/api/v1/repositories/${repositoryId}/indexing-jobs/${jobId}`);
}
