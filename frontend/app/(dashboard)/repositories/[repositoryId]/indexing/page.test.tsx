import { describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithProviders } from "@/test/render";
import { makeIndexingJob, makeRepository } from "@/test/factories";
import { RepositoryIndexingView } from "./page";

vi.mock("@/lib/realtime-context", () => ({
  useRealtime: () => ({ status: "open" }),
}));

vi.mock("@/lib/api/repositories", () => ({
  getRepositoryOverview: vi.fn(),
}));

vi.mock("@/lib/api/indexing", () => ({
  listIndexingJobs: vi.fn(),
  triggerIndexing: vi.fn(),
}));

import { getRepositoryOverview } from "@/lib/api/repositories";
import { listIndexingJobs, triggerIndexing } from "@/lib/api/indexing";

const repository = makeRepository({ id: "repo-1", full_name: "acme/widgets" });

function renderPage() {
  return renderWithProviders(<RepositoryIndexingView repositoryId="repo-1" />);
}

// Critical flow #7 — Index repository.
describe("RepositoryIndexingPage", () => {
  it("shows a 'not indexed yet' state and an enabled 'Index now' button when no job has run", async () => {
    vi.mocked(getRepositoryOverview).mockResolvedValueOnce({
      repository,
      recent_commits: [],
      open_pull_requests: [],
      open_issues: [],
    });
    vi.mocked(listIndexingJobs).mockResolvedValueOnce([]);
    renderPage();

    expect(await screen.findByText("Not indexed yet")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Index now" })).toBeEnabled();
  });

  it("triggers indexing and disables the button while a job is active", async () => {
    vi.mocked(getRepositoryOverview).mockResolvedValue({
      repository,
      recent_commits: [],
      open_pull_requests: [],
      open_issues: [],
    });
    vi.mocked(listIndexingJobs).mockResolvedValueOnce([]);
    const queuedJob = makeIndexingJob({ repository_id: "repo-1", status: "queued" });
    vi.mocked(triggerIndexing).mockResolvedValueOnce({ started: true, job: queuedJob });
    vi.mocked(listIndexingJobs).mockResolvedValueOnce([queuedJob]);

    const user = userEvent.setup();
    renderPage();

    const button = await screen.findByRole("button", { name: "Index now" });
    await user.click(button);

    await waitFor(() => expect(triggerIndexing).toHaveBeenCalledWith("repo-1"));
    expect(await screen.findByRole("button", { name: "Indexing…" })).toBeDisabled();
  });

  it("does not offer to re-index while a job is already running", async () => {
    vi.mocked(getRepositoryOverview).mockResolvedValueOnce({
      repository,
      recent_commits: [],
      open_pull_requests: [],
      open_issues: [],
    });
    vi.mocked(listIndexingJobs).mockResolvedValueOnce([
      makeIndexingJob({ repository_id: "repo-1", status: "running" }),
    ]);
    renderPage();

    expect(await screen.findByRole("button", { name: "Indexing…" })).toBeDisabled();
    expect(triggerIndexing).not.toHaveBeenCalled();
  });
});
