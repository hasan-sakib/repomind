import { apiFetch } from "@/lib/api-client";
import type { AnalyticsSnapshot } from "@/lib/types";

export function getAnalyticsSnapshot(repositoryId: string): Promise<AnalyticsSnapshot> {
  return apiFetch(`/api/v1/repositories/${repositoryId}/analytics`);
}

export function triggerAnalyticsSnapshot(
  repositoryId: string,
  options: { force?: boolean } = {},
): Promise<AnalyticsSnapshot> {
  const query = options.force ? "?force=true" : "";
  return apiFetch(`/api/v1/repositories/${repositoryId}/analytics${query}`, { method: "POST" });
}
