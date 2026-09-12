/**
 * Test data factories — small builder functions that return a fully-shaped
 * object with sane defaults, overridable per call. Used instead of copying
 * a full literal into every test: a test that only cares about `role`
 * shouldn't have to restate every other field of a Member, and when the
 * `Member` shape changes, only this file needs to change, not every test
 * that builds one. Keep these in sync with lib/types.ts.
 */
import type {
  Commit,
  Conversation,
  IndexingJob,
  Member,
  Organization,
  OrganizationMembership,
  PullRequest,
  PullRequestAnalysis,
  Repository,
  SourceReference,
  User,
} from "@/lib/types";

let counter = 0;
function nextId(prefix: string): string {
  counter += 1;
  return `${prefix}-${counter}`;
}

export function makeUser(overrides: Partial<User> = {}): User {
  const id = overrides.id ?? nextId("user");
  return {
    id,
    email: `${id}@example.com`,
    full_name: "Test User",
    avatar_url: null,
    email_verified: true,
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeOrganization(overrides: Partial<Organization> = {}): Organization {
  const id = overrides.id ?? nextId("org");
  return {
    id,
    name: "Acme Inc",
    slug: "acme-inc",
    plan: "free",
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeOrganizationMembership(
  overrides: Partial<OrganizationMembership> = {},
): OrganizationMembership {
  return {
    organization: makeOrganization(),
    role: "owner",
    ...overrides,
  };
}

export function makeMember(overrides: Partial<Member> = {}): Member {
  return {
    user: makeUser(),
    role: "developer",
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeRepository(overrides: Partial<Repository> = {}): Repository {
  const id = overrides.id ?? nextId("repo");
  return {
    id,
    full_name: "acme/widgets",
    name: "widgets",
    description: "A widget factory",
    language: "TypeScript",
    stargazers_count: 12,
    forks_count: 2,
    default_branch: "main",
    private: false,
    html_url: "https://github.com/acme/widgets",
    status: "ready",
    sync_error: null,
    last_synced_at: "2026-01-01T00:00:00Z",
    connected_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makePullRequest(overrides: Partial<PullRequest> = {}): PullRequest {
  return {
    number: 1,
    title: "Add feature",
    state: "open",
    author_login: "octocat",
    html_url: "https://github.com/acme/widgets/pull/1",
    head_sha: "a".repeat(40),
    github_created_at: "2026-01-01T00:00:00Z",
    github_updated_at: "2026-01-01T00:00:00Z",
    closed_at: null,
    merged_at: null,
    ...overrides,
  };
}

export function makePullRequestAnalysis(
  overrides: Partial<PullRequestAnalysis> = {},
): PullRequestAnalysis {
  return {
    id: nextId("pr-analysis"),
    head_sha: "a".repeat(40),
    status: "succeeded",
    risk_level: "low",
    summary: "Small, well-tested change.",
    affected_components: [],
    potential_concerns: [],
    recommended_tests: [],
    files_analyzed: [],
    model: "claude-opus-5",
    error: null,
    created_at: "2026-01-01T00:00:00Z",
    started_at: "2026-01-01T00:00:00Z",
    finished_at: "2026-01-01T00:00:05Z",
    ...overrides,
  };
}

export function makeIndexingJob(overrides: Partial<IndexingJob> = {}): IndexingJob {
  const id = overrides.id ?? nextId("job");
  return {
    id,
    repository_id: overrides.repository_id ?? nextId("repo"),
    trigger: "manual",
    commit_sha: "a".repeat(40),
    status: "succeeded",
    current_stage: "done",
    files_discovered: 100,
    files_processed: 100,
    files_skipped: 0,
    symbols_extracted: 500,
    chunks_created: 500,
    embeddings_generated: 500,
    started_at: "2026-01-01T00:00:00Z",
    finished_at: "2026-01-01T00:00:10Z",
    error: null,
    created_at: "2026-01-01T00:00:00Z",
    errors: [],
    ...overrides,
  };
}

export function makeSourceReference(overrides: Partial<SourceReference> = {}): SourceReference {
  return {
    source_type: "vector",
    rank: 1,
    score: 0.92,
    file_path: "src/auth/login.ts",
    start_line: 10,
    end_line: 20,
    symbol_name: "login",
    commit_sha: null,
    commit_url: null,
    ...overrides,
  };
}

export function makeCommit(overrides: Partial<Commit> = {}): Commit {
  return {
    sha: "a".repeat(40),
    message: "Fix bug",
    author_name: "Octocat",
    author_login: "octocat",
    html_url: "https://github.com/acme/widgets/commit/" + "a".repeat(40),
    authored_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

export function makeConversation(overrides: Partial<Conversation> = {}): Conversation {
  return {
    id: nextId("conversation"),
    repository_id: overrides.repository_id ?? nextId("repo"),
    title: "How does auth work?",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}
