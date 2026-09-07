/**
 * Placeholder data for the Phase 1 application shell.
 *
 * There is no auth, workspace, or repository backend yet (see
 * docs/architecture/backend-architecture.md for that design). Every export
 * here stands in for a real API response so the shell can be built and
 * reviewed end-to-end. Replace with real `apiFetch` calls once the
 * corresponding endpoints exist — see docs/api/api-design.md.
 */

export type RepositoryStatus = "pending" | "indexing" | "ready" | "failed";

export interface DemoWorkspace {
  id: string;
  name: string;
  slug: string;
  plan: "personal" | "team";
}

export interface DemoRepository {
  id: string;
  name: string;
  fullName: string;
  slug: string;
  status: RepositoryStatus;
  defaultBranch: string;
  lastIndexedAt: string | null;
  connectedAt: string;
}

export interface DemoNotification {
  id: string;
  title: string;
  description: string;
  createdAt: string;
  read: boolean;
}

export const demoUser = {
  name: "Jordan Avery",
  email: "jordan@example.com",
  avatarUrl: null as string | null,
};

export const demoWorkspaces: DemoWorkspace[] = [
  { id: "ws_1", name: "Jordan Avery", slug: "jordan-avery", plan: "personal" },
  { id: "ws_2", name: "Northwind Labs", slug: "northwind-labs", plan: "team" },
];

export const demoRepositories: DemoRepository[] = [
  {
    id: "repo_1",
    name: "repomind",
    fullName: "northwind-labs/repomind",
    slug: "repomind",
    status: "ready",
    defaultBranch: "main",
    lastIndexedAt: "2026-09-07T18:32:00Z",
    connectedAt: "2026-09-01T10:00:00Z",
  },
  {
    id: "repo_2",
    name: "billing-service",
    fullName: "northwind-labs/billing-service",
    slug: "billing-service",
    status: "indexing",
    defaultBranch: "main",
    lastIndexedAt: null,
    connectedAt: "2026-09-08T09:15:00Z",
  },
  {
    id: "repo_3",
    name: "design-tokens",
    fullName: "northwind-labs/design-tokens",
    slug: "design-tokens",
    status: "failed",
    defaultBranch: "trunk",
    lastIndexedAt: "2026-09-05T14:02:00Z",
    connectedAt: "2026-08-20T11:30:00Z",
  },
];

export const demoNotifications: DemoNotification[] = [
  {
    id: "notif_1",
    title: "billing-service is indexing",
    description: "Started after the connect action a few minutes ago.",
    createdAt: "2026-09-08T09:16:00Z",
    read: false,
  },
  {
    id: "notif_2",
    title: "design-tokens indexing failed",
    description: "The default branch could not be cloned. Retry from repository settings.",
    createdAt: "2026-09-05T14:05:00Z",
    read: false,
  },
  {
    id: "notif_3",
    title: "repomind finished indexing",
    description: "1,204 chunks embedded across 312 files.",
    createdAt: "2026-09-07T18:32:00Z",
    read: true,
  },
];

export const repositoryStatusLabel: Record<RepositoryStatus, string> = {
  pending: "Pending",
  indexing: "Indexing",
  ready: "Ready",
  failed: "Failed",
};
