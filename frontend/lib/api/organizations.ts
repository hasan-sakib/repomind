import { apiFetch } from "@/lib/api-client";
import type {
  ApiKey,
  ApiKeyCreated,
  AuditLogEntry,
  BillingInfo,
  Member,
  Organization,
  OrganizationMembership,
  Plan,
  Role,
  UsageSummary,
} from "@/lib/types";

export function listMyOrganizations(): Promise<OrganizationMembership[]> {
  return apiFetch("/api/v1/organizations");
}

export function createOrganization(name: string): Promise<Organization> {
  return apiFetch("/api/v1/organizations", { method: "POST", body: JSON.stringify({ name }) });
}

export function listMembers(organizationId: string): Promise<Member[]> {
  return apiFetch(`/api/v1/organizations/${organizationId}/members`);
}

export function addMember(
  organizationId: string,
  input: { email: string; role: Role },
): Promise<Member> {
  return apiFetch(`/api/v1/organizations/${organizationId}/members`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateMemberRole(
  organizationId: string,
  userId: string,
  role: Role,
): Promise<Member> {
  return apiFetch(`/api/v1/organizations/${organizationId}/members/${userId}`, {
    method: "PATCH",
    body: JSON.stringify({ role }),
  });
}

export function removeMember(organizationId: string, userId: string): Promise<void> {
  return apiFetch(`/api/v1/organizations/${organizationId}/members/${userId}`, {
    method: "DELETE",
  });
}

export function updateOrganization(organizationId: string, name: string): Promise<Organization> {
  return apiFetch(`/api/v1/organizations/${organizationId}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

export function setPlan(organizationId: string, plan: Plan): Promise<Organization> {
  return apiFetch(`/api/v1/organizations/${organizationId}/plan`, {
    method: "POST",
    body: JSON.stringify({ plan }),
  });
}

export function getUsageSummary(organizationId: string): Promise<UsageSummary> {
  return apiFetch(`/api/v1/organizations/${organizationId}/usage`);
}

export function getBillingInfo(organizationId: string): Promise<BillingInfo> {
  return apiFetch(`/api/v1/organizations/${organizationId}/billing`);
}

export function getAuditLogs(organizationId: string): Promise<AuditLogEntry[]> {
  return apiFetch(`/api/v1/organizations/${organizationId}/audit-logs`);
}

export function listApiKeys(organizationId: string): Promise<ApiKey[]> {
  return apiFetch(`/api/v1/organizations/${organizationId}/api-keys`);
}

export function createApiKey(
  organizationId: string,
  input: { name: string; role: Role },
): Promise<ApiKeyCreated> {
  return apiFetch(`/api/v1/organizations/${organizationId}/api-keys`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function revokeApiKey(organizationId: string, apiKeyId: string): Promise<void> {
  return apiFetch(`/api/v1/organizations/${organizationId}/api-keys/${apiKeyId}`, {
    method: "DELETE",
  });
}
