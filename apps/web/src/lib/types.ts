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
  head_sha: string;
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

export type MessageRole = "user" | "assistant";

export type MessageFeedback = "up" | "down";

export type QueryIntent = "explain" | "locate" | "dependency" | "history" | "general";

export const QUERY_INTENT_LABELS: Record<QueryIntent, string> = {
  explain: "Explaining",
  locate: "Locating",
  dependency: "Dependency lookup",
  history: "History search",
  general: "General",
};

export type RetrievalSourceType = "vector" | "dependency" | "git_history";

export interface SourceReference {
  source_type: RetrievalSourceType;
  rank: number;
  score: number | null;
  file_path: string | null;
  start_line: number | null;
  end_line: number | null;
  symbol_name: string | null;
  commit_sha: string | null;
  commit_url: string | null;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  feedback: MessageFeedback | null;
  created_at: string;
  intent: QueryIntent | null;
  sources: SourceReference[];
}

export interface Conversation {
  id: string;
  repository_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail {
  conversation: Conversation;
  messages: ChatMessage[];
}

export type NodeKind = "route" | "service" | "repository" | "model" | "schema" | "other";

export const NODE_KIND_LABELS: Record<NodeKind, string> = {
  route: "Route",
  service: "Service",
  repository: "Repository",
  model: "Model",
  schema: "Schema",
  other: "Other",
};

export type GraphNodeType = "package" | "file" | "database";

export interface GraphNode {
  id: string;
  node_type: GraphNodeType;
  label: string;
  kind: NodeKind | "database";
  path: string | null;
  file_id: string | null;
  language: string | null;
  file_count: number | null;
  symbol_count: number | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  weight: number;
}

export interface GraphView {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface SymbolSummary {
  id: string;
  symbol_type: string;
  name: string;
  start_line: number;
  end_line: number;
  signature: string | null;
  docstring: string | null;
}

export interface DependencyRef {
  file_id: string;
  path: string;
  matched_name: string;
}

export interface FileDetail {
  file_id: string;
  path: string;
  language: string | null;
  kind: NodeKind;
  commit_sha: string;
  symbols: SymbolSummary[];
  dependencies: DependencyRef[];
  dependents: DependencyRef[];
}

export interface ArchitectureSearchResult {
  file_id: string;
  path: string;
  package: string;
  matched_symbol_name: string | null;
}

export interface RecentCommit {
  sha: string;
  message: string;
  author_login: string | null;
  author_name: string | null;
  html_url: string;
  authored_at: string;
}

export type PRAnalysisStatus = "queued" | "running" | "succeeded" | "failed";

export const PR_ANALYSIS_STATUS_LABELS: Record<PRAnalysisStatus, string> = {
  queued: "Queued",
  running: "Analyzing…",
  succeeded: "Analyzed",
  failed: "Failed",
};

export type PRRiskLevel = "low" | "medium" | "high";

export const PR_RISK_LEVEL_LABELS: Record<PRRiskLevel, string> = {
  low: "Low risk",
  medium: "Medium risk",
  high: "High risk",
};

export interface AffectedComponent {
  name: string;
  file_paths: string[];
}

export interface PotentialConcern {
  description: string;
  file_path: string | null;
  symbol_name: string | null;
}

export interface RecommendedTest {
  description: string;
  existing_test_file: string | null;
}

export interface ChangedFile {
  path: string;
  status: string;
  additions: number;
  deletions: number;
}

export interface PullRequestAnalysis {
  id: string;
  status: PRAnalysisStatus;
  head_sha: string;
  risk_level: PRRiskLevel | null;
  summary: string | null;
  affected_components: AffectedComponent[];
  potential_concerns: PotentialConcern[];
  recommended_tests: RecommendedTest[];
  files_analyzed: ChangedFile[];
  model: string | null;
  error: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}
