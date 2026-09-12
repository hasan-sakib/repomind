import { describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithProviders } from "@/test/render";
import { makeRepository } from "@/test/factories";
import { DetailPanel } from "./detail-panel";
import type { FileDetail, GraphNode, RecentCommit } from "@/lib/types";

vi.mock("@/lib/api/architecture", () => ({
  getFileDetail: vi.fn(),
  getRecentChanges: vi.fn(),
}));

import { getFileDetail, getRecentChanges } from "@/lib/api/architecture";

const repository = makeRepository({ html_url: "https://github.com/acme/widgets" });

function fileNode(overrides: Partial<GraphNode> = {}): GraphNode {
  return {
    id: "file-1",
    node_type: "file",
    label: "evaluator.ts",
    kind: "service",
    path: "src/policy/evaluator.ts",
    file_id: "file-1",
    language: "TypeScript",
    file_count: null,
    symbol_count: 3,
    ...overrides,
  };
}

const fileDetail: FileDetail = {
  file_id: "file-1",
  path: "src/policy/evaluator.ts",
  language: "TypeScript",
  kind: "service",
  commit_sha: "a".repeat(40),
  symbols: [
    {
      id: "sym-1",
      symbol_type: "function",
      name: "evaluate",
      start_line: 10,
      end_line: 42,
      signature: null,
      docstring: null,
    },
  ],
  dependencies: [{ file_id: "file-2", path: "src/router/match.ts", matched_name: "match" }],
  dependents: [],
};

const recentCommits: RecentCommit[] = [
  {
    sha: "b".repeat(40),
    message: "Refactor evaluator",
    author_login: "alice",
    author_name: "Alice",
    html_url: "https://github.com/acme/widgets/commit/" + "b".repeat(40),
    authored_at: "2026-01-01T00:00:00Z",
  },
];

// Critical flow #10 — View architecture (the click-to-inspect detail panel).
describe("DetailPanel", () => {
  it("prompts to select a node when nothing is selected", () => {
    renderWithProviders(
      <DetailPanel node={null} repositoryId="repo-1" repository={repository} />,
    );
    expect(screen.getByText("Select a node to inspect its details.")).toBeInTheDocument();
  });

  it("shows a file node's symbols, dependencies, and recent commits", async () => {
    vi.mocked(getFileDetail).mockResolvedValueOnce(fileDetail);
    vi.mocked(getRecentChanges).mockResolvedValueOnce(recentCommits);

    renderWithProviders(
      <DetailPanel node={fileNode()} repositoryId="repo-1" repository={repository} />,
    );

    expect(await screen.findByText("evaluate")).toBeInTheDocument();
    expect(screen.getByText("src/router/match.ts")).toBeInTheDocument();
    expect(screen.getByText("Refactor evaluator")).toBeInTheDocument();
    expect(getFileDetail).toHaveBeenCalledWith("repo-1", "file-1");
  });

  it("links a symbol directly to its line range on GitHub", async () => {
    vi.mocked(getFileDetail).mockResolvedValueOnce(fileDetail);
    vi.mocked(getRecentChanges).mockResolvedValueOnce([]);

    renderWithProviders(
      <DetailPanel node={fileNode()} repositoryId="repo-1" repository={repository} />,
    );

    const link = await screen.findByRole("link", { name: "evaluate" });
    expect(link).toHaveAttribute(
      "href",
      "https://github.com/acme/widgets/blob/main/src/policy/evaluator.ts#L10-L42",
    );
  });

  it("expands a package node on request", async () => {
    const onExpandPackage = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(
      <DetailPanel
        node={{
          id: "pkg-1",
          node_type: "package",
          label: "src/policy",
          kind: "service",
          path: "src/policy",
          file_id: null,
          language: null,
          file_count: 18,
          symbol_count: null,
        }}
        repositoryId="repo-1"
        repository={repository}
        onExpandPackage={onExpandPackage}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Expand package" }));
    expect(onExpandPackage).toHaveBeenCalledWith("src/policy");
  });

  it("shows a fallback message when the file detail fails to load", async () => {
    vi.mocked(getFileDetail).mockRejectedValueOnce(new Error("boom"));
    vi.mocked(getRecentChanges).mockResolvedValueOnce([]);

    renderWithProviders(
      <DetailPanel node={fileNode()} repositoryId="repo-1" repository={repository} />,
    );

    await waitFor(() =>
      expect(
        screen.getByText("Couldn't load this file's details."),
      ).toBeInTheDocument(),
    );
  });
});
