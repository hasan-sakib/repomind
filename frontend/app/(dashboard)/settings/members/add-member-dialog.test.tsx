import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ApiError } from "@/lib/api-client";
import { AddMemberDialog } from "./page";

vi.mock("@/lib/api/organizations", () => ({
  addMember: vi.fn(),
}));

import { addMember } from "@/lib/api/organizations";

// Critical flow #4 — Invite member.
describe("AddMemberDialog", () => {
  it("adds a member with the selected role, then notifies and closes", async () => {
    vi.mocked(addMember).mockResolvedValueOnce({
      user: {
        id: "user-2",
        email: "bob@example.com",
        full_name: "Bob",
        avatar_url: null,
        email_verified: true,
        created_at: "2026-01-01T00:00:00Z",
      },
      role: "developer",
      created_at: "2026-01-01T00:00:00Z",
    });
    const onOpenChange = vi.fn();
    const onAdded = vi.fn();
    const user = userEvent.setup();
    render(
      <AddMemberDialog
        open
        onOpenChange={onOpenChange}
        organizationId="org-1"
        onAdded={onAdded}
      />,
    );

    await user.type(screen.getByLabelText("Email"), "bob@example.com");
    await user.click(screen.getByRole("button", { name: "Add member" }));

    await waitFor(() =>
      expect(addMember).toHaveBeenCalledWith("org-1", {
        email: "bob@example.com",
        role: "developer",
      }),
    );
    expect(onAdded).toHaveBeenCalledTimes(1);
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("shows a specific message when the invited email has no account yet", async () => {
    vi.mocked(addMember).mockRejectedValueOnce(
      new ApiError(404, "user_not_found", "not found"),
    );
    const user = userEvent.setup();
    render(
      <AddMemberDialog open onOpenChange={vi.fn()} organizationId="org-1" onAdded={vi.fn()} />,
    );

    await user.type(screen.getByLabelText("Email"), "ghost@example.com");
    await user.click(screen.getByRole("button", { name: "Add member" }));

    expect(
      await screen.findByText("No registered user with that email. They need to sign up first."),
    ).toBeInTheDocument();
  });

  it("shows a specific message when the organization's plan member limit is reached", async () => {
    vi.mocked(addMember).mockRejectedValueOnce(
      new ApiError(402, "plan_limit_reached", "Your Free plan allows up to 3 members."),
    );
    const user = userEvent.setup();
    render(
      <AddMemberDialog open onOpenChange={vi.fn()} organizationId="org-1" onAdded={vi.fn()} />,
    );

    await user.type(screen.getByLabelText("Email"), "new@example.com");
    await user.click(screen.getByRole("button", { name: "Add member" }));

    expect(
      await screen.findByText("Your Free plan allows up to 3 members."),
    ).toBeInTheDocument();
  });
});
