import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ErrorState } from "./error-state";

describe("ErrorState", () => {
  it("renders the default title and the given description", () => {
    render(<ErrorState description="Couldn't load repositories." />);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    expect(screen.getByText("Couldn't load repositories.")).toBeInTheDocument();
  });

  it("renders a custom title when given", () => {
    render(<ErrorState title="Couldn't load this repository" description="Try again." />);
    expect(screen.getByText("Couldn't load this repository")).toBeInTheDocument();
  });

  it("does not render a retry button when onRetry is omitted", () => {
    render(<ErrorState description="No retry available." />);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("calls onRetry exactly once when the retry button is clicked", async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(<ErrorState description="Something failed." onRetry={onRetry} />);

    await user.click(screen.getByRole("button", { name: "Try again" }));

    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
