import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { RepositoryStatusBadge } from "./status-badge";
import type { RepositoryStatus } from "@/lib/types";

describe("RepositoryStatusBadge", () => {
  const cases: [RepositoryStatus, string][] = [
    ["ready", "Ready"],
    ["syncing", "Syncing"],
    ["error", "Error"],
    ["pending", "Pending"],
  ];

  it.each(cases)("renders the label for status %s", (status, label) => {
    render(<RepositoryStatusBadge status={status} />);
    expect(screen.getByText(label)).toBeInTheDocument();
  });

  it("shows a pulsing indicator only while syncing", () => {
    const { container, rerender } = render(<RepositoryStatusBadge status="syncing" />);
    expect(container.querySelector(".animate-pulse")).not.toBeNull();

    rerender(<RepositoryStatusBadge status="ready" />);
    expect(container.querySelector(".animate-pulse")).toBeNull();
  });
});
