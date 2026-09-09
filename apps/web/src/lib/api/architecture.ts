import { apiFetch } from "@/lib/api-client";
import type { ArchitectureSearchResult, FileDetail, GraphView, RecentCommit } from "@/lib/types";

export function getPackageGraph(repositoryId: string): Promise<GraphView> {
  return apiFetch(`/api/v1/repositories/${repositoryId}/architecture/graph`);
}

export function getModuleGraph(repositoryId: string, packagePath: string): Promise<GraphView> {
  const query = new URLSearchParams({ package: packagePath });
  return apiFetch(`/api/v1/repositories/${repositoryId}/architecture/graph?${query}`);
}

export function getFileDetail(repositoryId: string, fileId: string): Promise<FileDetail> {
  return apiFetch(`/api/v1/repositories/${repositoryId}/architecture/files/${fileId}`);
}

export function getRecentChanges(
  repositoryId: string,
  fileId: string,
): Promise<RecentCommit[]> {
  return apiFetch(
    `/api/v1/repositories/${repositoryId}/architecture/files/${fileId}/recent-changes`,
  );
}

export function searchArchitecture(
  repositoryId: string,
  query: string,
): Promise<ArchitectureSearchResult[]> {
  const params = new URLSearchParams({ q: query });
  return apiFetch(`/api/v1/repositories/${repositoryId}/architecture/search?${params}`);
}
