export type Role = "owner" | "admin" | "developer" | "viewer";

export const ROLE_LABELS: Record<Role, string> = {
  owner: "Owner",
  admin: "Admin",
  developer: "Developer",
  viewer: "Viewer",
};

// Ordered highest to lowest privilege — mirrors app/domain/role.py on the backend.
export const ROLE_RANK: Record<Role, number> = {
  owner: 3,
  admin: 2,
  developer: 1,
  viewer: 0,
};

export function roleAtLeast(role: Role, minimum: Role): boolean {
  return ROLE_RANK[role] >= ROLE_RANK[minimum];
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  avatar_url: string | null;
  email_verified: boolean;
  created_at: string;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  created_at: string;
}

export interface OrganizationMembership {
  organization: Organization;
  role: Role;
}

export interface Member {
  user: User;
  role: Role;
  created_at: string;
}

export interface MeResponse {
  user: User;
  organizations: OrganizationMembership[];
}
