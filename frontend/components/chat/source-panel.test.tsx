import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { SourcePanel } from "./source-panel";
import { makeRepository, makeSourceReference } from "@/test/factories";

const repository = makeRepository({
  html_url: "https://github.com/acme/widgets",
  default_branch: "main",
});

// Critical flow #9 — View source reference.
describe("SourcePanel", () => {
  it("shows a placeholder before any sources arrive", () => {
    render(<SourcePanel sources={[]} repository={repository} activeRank={null} />);
    expect(
      screen.getByText("Sources for the assistant's answer will appear here."),
    ).toBeInTheDocument();
  });

  it("renders a vector-search source's file path and line range", () => {
    const source = makeSourceReference({
      rank: 1,
      source_type: "vector",
      file_path: "src/auth/login.ts",
      start_line: 10,
      end_line: 20,
      symbol_name: "login",
    });
    render(<SourcePanel sources={[source]} repository={repository} activeRank={null} />);

    expect(screen.getByText("src/auth/login.ts")).toBeInTheDocument();
    expect(screen.getByText("Lines 10-20 · login")).toBeInTheDocument();
  });

  it("links a file-backed source straight to the exact line range on GitHub", () => {
    const source = makeSourceReference({
      rank: 1,
      source_type: "vector",
      file_path: "src/auth/login.ts",
      start_line: 10,
      end_line: 20,
    });
    render(<SourcePanel sources={[source]} repository={repository} activeRank={null} />);

    expect(screen.getByRole("link", { name: "Open on GitHub" })).toHaveAttribute(
      "href",
      "https://github.com/acme/widgets/blob/main/src/auth/login.ts#L10-L20",
    );
  });

  it("links a git-history source to its commit URL instead of a blob URL", () => {
    const source = makeSourceReference({
      rank: 2,
      source_type: "git_history",
      file_path: null,
      start_line: null,
      end_line: null,
      commit_sha: "abc1234def",
      commit_url: "https://github.com/acme/widgets/commit/abc1234def",
    });
    render(<SourcePanel sources={[source]} repository={repository} activeRank={null} />);

    expect(screen.getByText("abc1234")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open on GitHub" })).toHaveAttribute(
      "href",
      "https://github.com/acme/widgets/commit/abc1234def",
    );
  });

  it("highlights the active source by rank", () => {
    const sources = [
      makeSourceReference({ rank: 1, file_path: "a.ts" }),
      makeSourceReference({ rank: 2, file_path: "b.ts" }),
    ];
    render(<SourcePanel sources={sources} repository={repository} activeRank={2} />);

    expect(screen.getByText("b.ts").closest("div.rounded-lg")).toHaveClass("border-brand");
    expect(screen.getByText("a.ts").closest("div.rounded-lg")).not.toHaveClass("border-brand");
  });
});
