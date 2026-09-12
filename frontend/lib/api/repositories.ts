import { apiFetch } from "@/lib/api-client";
import type {
  Branch,
  Commit,
  Issue,
  PullRequest,
  Repository,
  RepositoryOverview,
} from "@/lib/types";

export function listRepositories(organizationId: string): Promise<Repository[]> {
  return apiFetch(`/api/v1/organizations/${organizationId}/repositories`);
}

export function connectRepository(
  organizationId: string,
  input: { installation_id: string; github_repo_id: number; full_name: string },
): Promise<Repository> {
  return apiFetch(`/api/v1/organizations/${organizationId}/repositories`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function getRepositoryOverview(repositoryId: string): Promise<RepositoryOverview> {
  return apiFetch(`/api/v1/repositories/${repositoryId}`);
}

export function syncRepositoryNow(repositoryId: string): Promise<{ started: boolean }> {
  return apiFetch(`/api/v1/repositories/${repositoryId}/sync`, { method: "POST" });
}

export function disconnectRepository(repositoryId: string): Promise<void> {
  return apiFetch(`/api/v1/repositories/${repositoryId}`, { method: "DELETE" });
}

export function listBranches(repositoryId: string): Promise<Branch[]> {
  return apiFetch(`/api/v1/repositories/${repositoryId}/branches`);
}

export function listCommits(repositoryId: string, limit = 20): Promise<Commit[]> {
  return apiFetch(`/api/v1/repositories/${repositoryId}/commits?limit=${limit}`);
}

export function listPullRequests(
  repositoryId: string,
  state?: "open" | "closed",
): Promise<PullRequest[]> {
  const query = state ? `?state=${state}` : "";
  return apiFetch(`/api/v1/repositories/${repositoryId}/pull-requests${query}`);
}

export function listIssues(repositoryId: string, state?: "open" | "closed"): Promise<Issue[]> {
  const query = state ? `?state=${state}` : "";
  return apiFetch(`/api/v1/repositories/${repositoryId}/issues${query}`);
}
