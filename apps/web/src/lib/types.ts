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

export type RepositoryStatus = "pending" | "syncing" | "ready" | "error";

export const REPOSITORY_STATUS_LABELS: Record<RepositoryStatus, string> = {
  pending: "Pending",
  syncing: "Syncing",
  ready: "Ready",
  error: "Error",
};

export interface Installation {
  id: string;
  account_login: string;
  account_type: string;
}

export interface AvailableRepository {
  github_repo_id: number;
  full_name: string;
  name: string;
  private: boolean;
  description: string | null;
}

export interface Repository {
  id: string;
  full_name: string;
  name: string;
  description: string | null;
  language: string | null;
  stargazers_count: number;
  forks_count: number;
  default_branch: string;
  private: boolean;
  html_url: string;
  status: RepositoryStatus;
  sync_error: string | null;
  last_synced_at: string | null;
  connected_at: string;
}

export interface Branch {
  name: string;
  commit_sha: string;
  is_default: boolean;
}

export interface Commit {
  sha: string;
  message: string;
  author_name: string | null;
  author_login: string | null;
  html_url: string;
  authored_at: string;
}

export interface PullRequest {
  number: number;
  title: string;
  state: string;
  author_login: string | null;
  html_url: string;
  github_created_at: string;
  github_updated_at: string;
  closed_at: string | null;
  merged_at: string | null;
}

export interface Issue {
  number: number;
  title: string;
  state: string;
  author_login: string | null;
  html_url: string;
  github_created_at: string;
  github_updated_at: string;
  closed_at: string | null;
}

export interface RepositoryOverview {
  repository: Repository;
  recent_commits: Commit[];
  open_pull_requests: PullRequest[];
  open_issues: Issue[];
}
