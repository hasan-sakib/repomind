import { FolderGitIcon } from "lucide-react";
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { EmptyState } from "./empty-state";

describe("EmptyState", () => {
  it("renders the title and description", () => {
    render(
      <EmptyState
        icon={FolderGitIcon}
        title="No repositories connected"
        description="Connect a repository to get started."
      />,
    );
    expect(screen.getByText("No repositories connected")).toBeInTheDocument();
    expect(screen.getByText("Connect a repository to get started.")).toBeInTheDocument();
  });

  it("renders an action when one is provided", () => {
    render(
      <EmptyState
        icon={FolderGitIcon}
        title="No repositories connected"
        description="Connect a repository to get started."
        action={<button>Connect repository</button>}
      />,
    );
    expect(screen.getByRole("button", { name: "Connect repository" })).toBeInTheDocument();
  });

  it("renders no action when none is provided", () => {
    render(
      <EmptyState icon={FolderGitIcon} title="Nothing here" description="Nothing to show." />,
    );
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
