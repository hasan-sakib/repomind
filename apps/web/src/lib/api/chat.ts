import { apiFetch } from "@/lib/api-client";
import { postSSE } from "@/lib/sse";
import type {
  ChatMessage,
  Conversation,
  ConversationDetail,
  MessageFeedback,
  QueryIntent,
  SourceReference,
} from "@/lib/types";

export function createConversation(repositoryId: string): Promise<Conversation> {
  return apiFetch(`/api/v1/repositories/${repositoryId}/conversations`, { method: "POST" });
}

export function listConversations(repositoryId: string): Promise<Conversation[]> {
  return apiFetch(`/api/v1/repositories/${repositoryId}/conversations`);
}

export function getConversation(
  repositoryId: string,
  conversationId: string,
): Promise<ConversationDetail> {
  return apiFetch(`/api/v1/repositories/${repositoryId}/conversations/${conversationId}`);
}

export function setMessageFeedback(
  repositoryId: string,
  conversationId: string,
  messageId: string,
  feedback: MessageFeedback | null,
): Promise<ChatMessage> {
  return apiFetch(
    `/api/v1/repositories/${repositoryId}/conversations/${conversationId}/messages/${messageId}/feedback`,
    { method: "PATCH", body: JSON.stringify({ feedback }) },
  );
}

export type ChatStreamEvent =
  | { type: "sources"; sources: SourceReference[] }
  | { type: "token"; text: string }
  | { type: "done"; message_id: string; run_id: string }
  | { type: "error"; message: string };

async function* toStreamEvents(
  frames: AsyncGenerator<{ event: string; data: string }>,
): AsyncGenerator<ChatStreamEvent> {
  for await (const frame of frames) {
    yield JSON.parse(frame.data) as ChatStreamEvent;
  }
}

export function askQuestion(
  repositoryId: string,
  conversationId: string,
  query: string,
): AsyncGenerator<ChatStreamEvent> {
  return toStreamEvents(
    postSSE(`/api/v1/repositories/${repositoryId}/conversations/${conversationId}/messages`, {
      query,
    }),
  );
}

export function regenerateAnswer(
  repositoryId: string,
  conversationId: string,
  userMessageId: string,
): AsyncGenerator<ChatStreamEvent> {
  return toStreamEvents(
    postSSE(
      `/api/v1/repositories/${repositoryId}/conversations/${conversationId}` +
        `/messages/${userMessageId}/regenerate`,
      {},
    ),
  );
}

// Re-exported so components importing from "@/lib/api/chat" don't also
// need "@/lib/types" just for this one type used in event handling.
export type { QueryIntent };
