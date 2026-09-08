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

export type IndexingJobStatus = "queued" | "running" | "succeeded" | "failed" | "partial";

export const INDEXING_JOB_STATUS_LABELS: Record<IndexingJobStatus, string> = {
  queued: "Queued",
  running: "Indexing",
  succeeded: "Indexed",
  failed: "Failed",
  partial: "Indexed with errors",
};

export type IndexingTrigger = "initial" | "manual" | "webhook";

export const INDEXING_TRIGGER_LABELS: Record<IndexingTrigger, string> = {
  initial: "Initial index",
  manual: "Manual",
  webhook: "Push",
};

export type IndexingStage =
  | "fetching"
  | "discovering"
  | "filtering"
  | "parsing"
  | "chunking"
  | "embedding"
  | "done";

export const INDEXING_STAGE_LABELS: Record<IndexingStage, string> = {
  fetching: "Fetching repository",
  discovering: "Discovering files",
  filtering: "Filtering files",
  parsing: "Parsing code",
  chunking: "Chunking",
  embedding: "Generating embeddings",
  done: "Done",
};

// Ordered by pipeline position — used to render a stage progress track.
export const INDEXING_STAGE_ORDER: IndexingStage[] = [
  "fetching",
  "discovering",
  "filtering",
  "parsing",
  "chunking",
  "embedding",
  "done",
];

export interface IndexingErrorEntry {
  id: string;
  file_path: string | null;
  stage: IndexingStage;
  message: string;
  created_at: string;
}

export interface IndexingJob {
  id: string;
  repository_id: string;
  status: IndexingJobStatus;
  trigger: IndexingTrigger;
  commit_sha: string;
  current_stage: IndexingStage | null;
  files_discovered: number;
  files_processed: number;
  files_skipped: number;
  symbols_extracted: number;
  chunks_created: number;
  embeddings_generated: number;
  started_at: string | null;
  finished_at: string | null;
  error: string | null;
  created_at: string;
  errors: IndexingErrorEntry[];
}

export interface TriggerIndexingResponse {
  started: boolean;
  job: IndexingJob;
}
