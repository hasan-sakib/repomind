import { describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithProviders } from "@/test/render";
import { makeOrganizationMembership, makeRepository } from "@/test/factories";
import ConnectRepositoryPage from "./page";

const push = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh: vi.fn() }),
}));

vi.mock("@/lib/api/github", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/github")>("@/lib/api/github");
  return {
    ...actual,
    listInstallations: vi.fn(),
    listAvailableRepositories: vi.fn(),
  };
});

vi.mock("@/lib/api/repositories", () => ({
  connectRepository: vi.fn(),
}));

import { githubInstallUrl, listAvailableRepositories, listInstallations } from "@/lib/api/github";
import { connectRepository } from "@/lib/api/repositories";

const org = makeOrganizationMembership();
const organizationId = org.organization.id;

function renderPage() {
  return renderWithProviders(<ConnectRepositoryPage />, { organizations: [org] });
}

// Critical flows #5 (Connect GitHub) and #6 (Connect repository).
describe("ConnectRepositoryPage", () => {
  it("prompts to connect GitHub when no App installation exists yet", async () => {
    vi.mocked(listInstallations).mockResolvedValueOnce([]);
    renderPage();

    expect(await screen.findByText("No GitHub App installation yet")).toBeInTheDocument();
    const link = screen.getByRole("button", { name: "Connect GitHub" });
    expect(link).toHaveAttribute("href", githubInstallUrl(organizationId));
  });

  it("lists available repositories once an installation exists, and connecting one navigates to it", async () => {
    vi.mocked(listInstallations).mockResolvedValueOnce([
      { id: "install-1", account_login: "acme", account_type: "Organization" },
    ]);
    vi.mocked(listAvailableRepositories).mockResolvedValueOnce([
      {
        github_repo_id: 123,
        full_name: "acme/widgets",
        name: "widgets",
        private: true,
        description: "A widget factory",
      },
    ]);
    const connectedRepo = makeRepository({ id: "repo-42", full_name: "acme/widgets" });
    vi.mocked(connectRepository).mockResolvedValueOnce(connectedRepo);

    const user = userEvent.setup();
    renderPage();

    expect(await screen.findByText("acme/widgets")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Connect" }));

    await waitFor(() =>
      expect(connectRepository).toHaveBeenCalledWith(organizationId, {
        installation_id: "install-1",
        github_repo_id: 123,
        full_name: "acme/widgets",
      }),
    );
    expect(push).toHaveBeenCalledWith("/repositories/repo-42");
  });

  it("shows an empty state when every accessible repository is already connected", async () => {
    vi.mocked(listInstallations).mockResolvedValueOnce([
      { id: "install-1", account_login: "acme", account_type: "Organization" },
    ]);
    vi.mocked(listAvailableRepositories).mockResolvedValueOnce([]);
    renderPage();

    expect(
      await screen.findByText("Every accessible repository is already connected"),
    ).toBeInTheDocument();
  });
});
