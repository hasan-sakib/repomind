import { describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithProviders } from "@/test/render";
import { makePullRequest, makePullRequestAnalysis, makeRepository } from "@/test/factories";
import { PullRequestDetailView } from "./page";
import { ApiError } from "@/lib/api-client";

vi.mock("@/lib/realtime-context", () => ({
  useRealtime: () => ({ status: "open" }),
}));

vi.mock("@/lib/api/repositories", () => ({
  getRepositoryOverview: vi.fn(),
}));

vi.mock("@/lib/api/pull-requests", () => ({
  getPullRequest: vi.fn(),
  getPullRequestAnalysis: vi.fn(),
  triggerPullRequestAnalysis: vi.fn(),
}));

import { getRepositoryOverview } from "@/lib/api/repositories";
import {
  getPullRequest,
  getPullRequestAnalysis,
  triggerPullRequestAnalysis,
} from "@/lib/api/pull-requests";

const repository = makeRepository({ id: "repo-1" });
const pullRequest = makePullRequest({ number: 42, title: "Add rate limiting" });

function renderPage() {
  return renderWithProviders(<PullRequestDetailView repositoryId="repo-1" number={42} />);
}

// Critical flow #11 — Analyze PR.
describe("PullRequestDetailView", () => {
  it("offers to analyze a PR that has never been analyzed, and shows the result once it has", async () => {
    vi.mocked(getRepositoryOverview).mockResolvedValue({
      repository,
      recent_commits: [],
      open_pull_requests: [],
      open_issues: [],
    });
    vi.mocked(getPullRequest).mockResolvedValue(pullRequest);
    vi.mocked(getPullRequestAnalysis).mockRejectedValueOnce(
      new ApiError(404, "pull_request_analysis_not_found", "not found"),
    );
    const analysis = makePullRequestAnalysis({
      risk_level: "medium",
      summary: "Adds a Redis-backed limiter to the login route.",
    });
    vi.mocked(triggerPullRequestAnalysis).mockResolvedValueOnce(analysis);

    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("Not analyzed yet")).toBeInTheDocument();
    // Both the header action and the empty-state action offer this button.
    await user.click(screen.getAllByRole("button", { name: "Analyze this PR" })[0]);

    await waitFor(() =>
      expect(triggerPullRequestAnalysis).toHaveBeenCalledWith("repo-1", 42, { force: false }),
    );
    expect(
      await screen.findByText("Adds a Redis-backed limiter to the login route."),
    ).toBeInTheDocument();
  });

  it("shows the existing analysis without re-triggering when one already exists", async () => {
    vi.mocked(getRepositoryOverview).mockResolvedValue({
      repository,
      recent_commits: [],
      open_pull_requests: [],
      open_issues: [],
    });
    vi.mocked(getPullRequest).mockResolvedValue(pullRequest);
    vi.mocked(getPullRequestAnalysis).mockResolvedValueOnce(
      makePullRequestAnalysis({ summary: "Looks safe." }),
    );

    renderPage();

    expect(await screen.findByText("Looks safe.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Re-analyze" })).toBeInTheDocument();
    expect(triggerPullRequestAnalysis).not.toHaveBeenCalled();
  });
});
