import { apiFetch } from "@/lib/api-client";
import type { AvailableRepository, Installation } from "@/lib/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function githubInstallUrl(organizationId: string): string {
  return `${API_BASE_URL}/api/v1/organizations/${organizationId}/github/install`;
}

export function listInstallations(organizationId: string): Promise<Installation[]> {
  return apiFetch(`/api/v1/organizations/${organizationId}/github/installations`);
}

export function listAvailableRepositories(
  organizationId: string,
  installationId: string,
): Promise<AvailableRepository[]> {
  return apiFetch(
    `/api/v1/organizations/${organizationId}/github/installations/${installationId}/available-repositories`,
  );
}
