import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ApiError } from "@/lib/api-client";
import LoginPage from "./page";

const push = vi.fn();
const refresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, refresh }),
}));

vi.mock("@/lib/api/auth", () => ({
  login: vi.fn(),
}));

vi.mock("@/components/auth/github-continue-link", () => ({
  GitHubContinueLink: () => null,
}));

import { login } from "@/lib/api/auth";

// Critical flow #2 — Login.
describe("LoginPage", () => {
  it("shows field errors instead of submitting when the form is invalid", async () => {
    const user = userEvent.setup();
    render(<LoginPage />);

    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Enter a valid email address")).toBeInTheDocument();
    expect(login).not.toHaveBeenCalled();
  });

  it("logs in and redirects to the dashboard on success", async () => {
    vi.mocked(login).mockResolvedValueOnce({
      user: {
        id: "user-1",
        email: "ada@example.com",
        full_name: "Ada",
        avatar_url: null,
        email_verified: true,
        created_at: "2026-01-01T00:00:00Z",
      },
    });
    const user = userEvent.setup();
    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "correct-horse-battery");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    await waitFor(() => expect(login).toHaveBeenCalledWith({
      email: "ada@example.com",
      password: "correct-horse-battery",
    }));
    expect(push).toHaveBeenCalledWith("/dashboard");
  });

  it("shows a generic error and does not navigate on invalid credentials", async () => {
    vi.mocked(login).mockRejectedValueOnce(
      new ApiError(401, "invalid_credentials", "Invalid credentials"),
    );
    const user = userEvent.setup();
    render(<LoginPage />);

    await user.type(screen.getByLabelText("Email"), "ada@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong-password");
    await user.click(screen.getByRole("button", { name: "Sign in" }));

    expect(await screen.findByText("Invalid email or password.")).toBeInTheDocument();
    expect(push).not.toHaveBeenCalled();
  });
});
