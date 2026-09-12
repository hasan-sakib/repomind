import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ApiError } from "@/lib/api-client";
import RegisterPage from "./page";

const push = vi.fn();
const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
}));

vi.mock("@/lib/api/auth", () => ({
  register: vi.fn(),
}));

vi.mock("@/components/auth/github-continue-link", () => ({
  GitHubContinueLink: () => null,
}));

import { register } from "@/lib/api/auth";

// Critical flow #1 — Register.
describe("RegisterPage", () => {
  it("shows field errors instead of submitting when the form is invalid", async () => {
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(await screen.findByText("Enter your name")).toBeInTheDocument();
    expect(register).not.toHaveBeenCalled();
  });

  it("registers and redirects to the dashboard on success", async () => {
    vi.mocked(register).mockResolvedValueOnce({
      user: {
        id: "user-1",
        email: "ada@example.com",
        full_name: "Ada Lovelace",
        avatar_url: null,
        email_verified: false,
        created_at: "2026-01-01T00:00:00Z",
      },
    });
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Full name"), "Ada Lovelace");
    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-horse-battery");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    await waitFor(() =>
      expect(register).toHaveBeenCalledWith({
        full_name: "Ada Lovelace",
        email: "ada@example.com",
        password: "correct-horse-battery",
      }),
    );
    expect(push).toHaveBeenCalledWith("/dashboard");
  });

  it("shows a field-level error when the email is already registered", async () => {
    vi.mocked(register).mockRejectedValueOnce(
      new ApiError(409, "email_already_registered", "Already registered"),
    );
    const user = userEvent.setup();
    render(<RegisterPage />);

    await user.type(screen.getByLabelText("Full name"), "Ada Lovelace");
    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-horse-battery");
    await user.click(screen.getByRole("button", { name: "Create account" }));

    expect(
      await screen.findByText("An account with this email already exists"),
    ).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });
});
