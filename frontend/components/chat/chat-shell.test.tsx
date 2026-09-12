import { describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { renderWithProviders } from "@/test/render";
import { makeConversation, makeRepository, makeSourceReference } from "@/test/factories";
import { ChatShell } from "./chat-shell";
import type { ChatStreamEvent } from "@/lib/api/chat";

const replace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace, push: vi.fn(), refresh: vi.fn() }),
}));

vi.mock("@/lib/api/repositories", () => ({
  getRepositoryOverview: vi.fn(),
}));

vi.mock("@/lib/api/chat", () => ({
  listConversations: vi.fn(),
  createConversation: vi.fn(),
  getConversation: vi.fn(),
  askQuestion: vi.fn(),
  regenerateAnswer: vi.fn(),
  setMessageFeedback: vi.fn(),
}));

import { getRepositoryOverview } from "@/lib/api/repositories";
import { askQuestion, createConversation, listConversations } from "@/lib/api/chat";

async function* fakeStream(events: ChatStreamEvent[]) {
  for (const event of events) {
    yield event;
  }
}

const repository = makeRepository({ id: "repo-1", full_name: "acme/widgets" });

function renderChat() {
  return renderWithProviders(<ChatShell repositoryId="repo-1" conversationId={null} />);
}

// Critical flow #8 — Ask AI question.
describe("ChatShell", () => {
  it("streams an answer with citations and shows the send button disabled while it does", async () => {
    vi.mocked(getRepositoryOverview).mockResolvedValue({
      repository,
      recent_commits: [],
      open_pull_requests: [],
      open_issues: [],
    });
    vi.mocked(listConversations).mockResolvedValue([]);
    const conversation = makeConversation({ id: "conv-1", repository_id: "repo-1" });
    vi.mocked(createConversation).mockResolvedValueOnce(conversation);

    const source = makeSourceReference({ rank: 1, file_path: "src/auth/login.ts" });
    vi.mocked(askQuestion).mockReturnValueOnce(
      fakeStream([
        { type: "sources", sources: [source] },
        { type: "token", text: "Auth flows through " },
        { type: "token", text: "the login handler." },
        { type: "done", message_id: "assistant-msg-1", run_id: "run-1" },
      ]),
    );

    const user = userEvent.setup();
    renderChat();

    const textbox = await screen.findByPlaceholderText("Ask about this codebase…");
    await user.type(textbox, "How does authentication work?");
    await user.click(screen.getByRole("button", { name: "Send" }));

    expect(await screen.findByText("How does authentication work?")).toBeInTheDocument();
    await waitFor(() =>
      expect(askQuestion).toHaveBeenCalledWith(
        "repo-1",
        "conv-1",
        "How does authentication work?",
      ),
    );

    expect(
      await screen.findByText("Auth flows through the login handler."),
    ).toBeInTheDocument();
    expect(screen.getByText("src/auth/login.ts")).toBeInTheDocument();

    // Only adopts the conversation's permanent URL after streaming finishes.
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/repositories/repo-1/chat/conv-1"));
  });

  it("does not let the user send an empty question", async () => {
    vi.mocked(getRepositoryOverview).mockResolvedValue({
      repository,
      recent_commits: [],
      open_pull_requests: [],
      open_issues: [],
    });
    vi.mocked(listConversations).mockResolvedValue([]);

    renderChat();
    expect(await screen.findByRole("button", { name: "Send" })).toBeDisabled();
    expect(askQuestion).not.toHaveBeenCalled();
  });
});
