import { apiFetch } from "@/lib/api-client";
import type { Member, Organization, OrganizationMembership, Role } from "@/lib/types";

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
