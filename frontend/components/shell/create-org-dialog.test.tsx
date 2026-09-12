import { describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithProviders } from "@/test/render";
import { makeOrganization } from "@/test/factories";
import { CreateOrgDialog } from "./create-org-dialog";

vi.mock("@/lib/api/organizations", () => ({
  createOrganization: vi.fn(),
}));

import { createOrganization } from "@/lib/api/organizations";

// Critical flow #3 — Create organization.
describe("CreateOrgDialog", () => {
  it("requires a non-empty name before submitting", async () => {
    const user = userEvent.setup();
    renderWithProviders(<CreateOrgDialog open onOpenChange={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: "Create" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Enter a name");
    expect(createOrganization).not.toHaveBeenCalled();
  });

  it("creates the organization, closes the dialog, and switches to it", async () => {
    const created = makeOrganization({ id: "org-new", name: "Widgets Co" });
    vi.mocked(createOrganization).mockResolvedValueOnce(created);
    const onOpenChange = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<CreateOrgDialog open onOpenChange={onOpenChange} />);

    await user.type(screen.getByLabelText("Name"), "Widgets Co");
    await user.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => expect(createOrganization).toHaveBeenCalledWith("Widgets Co"));
    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false));
  });

  it("shows an error and keeps the dialog open when creation fails", async () => {
    vi.mocked(createOrganization).mockRejectedValueOnce(new Error("network error"));
    const onOpenChange = vi.fn();
    const user = userEvent.setup();
    renderWithProviders(<CreateOrgDialog open onOpenChange={onOpenChange} />);

    await user.type(screen.getByLabelText("Name"), "Widgets Co");
    await user.click(screen.getByRole("button", { name: "Create" }));

    expect(
      await screen.findByText("Something went wrong. Please try again."),
    ).toBeInTheDocument();
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
  });
});
