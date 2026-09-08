"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageSquareIcon } from "lucide-react";

import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/error-state";
import { ChatInput } from "@/components/chat/chat-input";
import { ConversationList } from "@/components/chat/conversation-list";
import { MessageItem } from "@/components/chat/message-item";
import { SourcePanel } from "@/components/chat/source-panel";
import {
  askQuestion,
  createConversation,
  getConversation,
  listConversations,
  regenerateAnswer,
  setMessageFeedback,
} from "@/lib/api/chat";
import { getRepositoryOverview } from "@/lib/api/repositories";
import type { ChatMessage, MessageFeedback, SourceReference } from "@/lib/types";

interface LocalMessage extends ChatMessage {
  clientKey: string;
}

function newClientKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2);
}

export function ChatShell({
  repositoryId,
  conversationId,
}: {
  repositoryId: string;
  conversationId: string | null;
}) {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [messages, setMessages] = useState<LocalMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [focus, setFocus] = useState<{ messageId: string; rank: number | null } | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const hydratedFor = useRef<string | null>(null);

  const overviewQuery = useQuery({
    queryKey: ["repository-overview", repositoryId],
    queryFn: () => getRepositoryOverview(repositoryId),
  });

  const conversationsQuery = useQuery({
    queryKey: ["conversations", repositoryId],
    queryFn: () => listConversations(repositoryId),
  });

  const detailQuery = useQuery({
    queryKey: ["conversation", repositoryId, conversationId],
    queryFn: () => getConversation(repositoryId, conversationId as string),
    enabled: conversationId !== null,
  });

  // Hydrate local (streamable) state from the fetched conversation once
  // per conversation id — after that, local state is the source of truth
  // so an in-flight stream isn't clobbered by a background refetch.
  // `conversationId === null` needs no reset here: the "new conversation"
  // and "existing conversation" routes are different page.tsx files, so
  // Next.js already mounts a fresh ChatShell (fresh useState) when
  // switching between them — see handleAsk's comment on why the URL
  // update is deferred until after streaming finishes, which is what
  // keeps that mount boundary from cutting off an in-flight stream.
  useEffect(() => {
    if (conversationId !== null && detailQuery.data && hydratedFor.current !== conversationId) {
      setMessages(detailQuery.data.messages.map((m) => ({ ...m, clientKey: newClientKey() })));
      hydratedFor.current = conversationId;
    }
  }, [conversationId, detailQuery.data]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const runStream = async (
    stream: AsyncGenerator<
      | { type: "sources"; sources: SourceReference[] }
      | { type: "token"; text: string }
      | { type: "done"; message_id: string; run_id: string }
      | { type: "error"; message: string }
    >,
    assistantClientKey: string,
  ) => {
    setIsStreaming(true);
    setStreamError(null);
    try {
      for await (const event of stream) {
        if (event.type === "sources") {
          setMessages((prev) =>
            prev.map((m) =>
              m.clientKey === assistantClientKey ? { ...m, sources: event.sources } : m,
            ),
          );
          setFocus({ messageId: assistantClientKey, rank: null });
        } else if (event.type === "token") {
          setMessages((prev) =>
            prev.map((m) =>
              m.clientKey === assistantClientKey
                ? { ...m, content: m.content + event.text }
                : m,
            ),
          );
        } else if (event.type === "done") {
          setMessages((prev) =>
            prev.map((m) =>
              m.clientKey === assistantClientKey ? { ...m, id: event.message_id } : m,
            ),
          );
          setFocus({ messageId: assistantClientKey, rank: null });
          void queryClient.invalidateQueries({ queryKey: ["conversations", repositoryId] });
        } else if (event.type === "error") {
          setStreamError(event.message);
        }
      }
    } catch (err) {
      setStreamError(err instanceof Error ? err.message : "The connection dropped.");
    } finally {
      setIsStreaming(false);
    }
  };

  const handleAsk = async (query: string) => {
    const userKey = newClientKey();
    const assistantKey = newClientKey();
    const now = new Date().toISOString();
    setMessages((prev) => [
      ...prev,
      { clientKey: userKey, id: userKey, role: "user", content: query, feedback: null, created_at: now, intent: null, sources: [] },
      { clientKey: assistantKey, id: assistantKey, role: "assistant", content: "", feedback: null, created_at: now, intent: null, sources: [] },
    ]);

    let targetConversationId = conversationId;
    if (targetConversationId === null) {
      const conversation = await createConversation(repositoryId);
      targetConversationId = conversation.id;
      void queryClient.invalidateQueries({ queryKey: ["conversations", repositoryId] });
    }

    await runStream(askQuestion(repositoryId, targetConversationId, query), assistantKey);

    // Adopt the conversation's permanent URL only once streaming has
    // finished — `/chat` and `/chat/[conversationId]` are different
    // page.tsx files, so navigating mid-stream would unmount this
    // component (and the in-flight answer) before it finished arriving.
    if (conversationId === null) {
      router.replace(`/repositories/${repositoryId}/chat/${targetConversationId}`);
    }
  };

  const handleRegenerate = async (userMessageId: string) => {
    if (conversationId === null) return;
    const assistantKey = newClientKey();
    const now = new Date().toISOString();
    setMessages((prev) => [
      ...prev,
      { clientKey: assistantKey, id: assistantKey, role: "assistant", content: "", feedback: null, created_at: now, intent: null, sources: [] },
    ]);
    await runStream(regenerateAnswer(repositoryId, conversationId, userMessageId), assistantKey);
  };

  const handleFeedback = async (messageId: string, feedback: MessageFeedback | null) => {
    if (conversationId === null) return;
    setMessages((prev) => prev.map((m) => (m.id === messageId ? { ...m, feedback } : m)));
    await setMessageFeedback(repositoryId, conversationId, messageId, feedback);
  };

  if (overviewQuery.isPending || conversationsQuery.isPending) {
    return (
      <div className="flex h-full items-center justify-center">
        <Skeleton className="h-8 w-48" />
      </div>
    );
  }

  if (overviewQuery.isError || conversationsQuery.isError) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <ErrorState
          title="Couldn't load chat"
          description="It may have been disconnected, or you may no longer have access."
          onRetry={() => {
            overviewQuery.refetch();
            conversationsQuery.refetch();
          }}
        />
      </div>
    );
  }

  const { repository } = overviewQuery.data;
  const lastAssistantKey = [...messages].reverse().find((m) => m.role === "assistant")?.clientKey;
  const focusedMessage =
    (focus && messages.find((m) => m.clientKey === focus.messageId)) ??
    [...messages].reverse().find((m) => m.role === "assistant" && m.sources.length > 0) ??
    null;

  return (
    <div className="flex h-full min-h-0">
      <aside className="hidden w-56 shrink-0 border-r border-border md:block">
        <ConversationList
          repositoryId={repositoryId}
          conversations={conversationsQuery.data}
          activeConversationId={conversationId}
        />
      </aside>

      <main className="flex min-h-0 min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-2 border-b border-border px-4 py-2.5">
          <MessageSquareIcon className="size-3.5 text-muted-foreground" />
          <span className="truncate text-sm font-medium">{repository.full_name}</span>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          {messages.length === 0 ? (
            <EmptyState repositoryName={repository.name} onAsk={handleAsk} />
          ) : (
            <div className="mx-auto flex max-w-3xl flex-col gap-4">
              {messages.map((message, index) => (
                <MessageItem
                  key={message.clientKey}
                  message={message}
                  isStreaming={isStreaming && message.clientKey === lastAssistantKey}
                  canRegenerate={
                    !isStreaming &&
                    message.role === "assistant" &&
                    message.clientKey === lastAssistantKey &&
                    index > 0
                  }
                  onRegenerate={() => handleRegenerate(messages[index - 1].id)}
                  onFeedback={(feedback) => handleFeedback(message.id, feedback)}
                  onCitationClick={(rank) => setFocus({ messageId: message.clientKey, rank })}
                />
              ))}
              {streamError && (
                <p className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-sm text-destructive">
                  {streamError}
                </p>
              )}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <div className="mx-auto w-full max-w-3xl">
          <ChatInput onSubmit={handleAsk} disabled={isStreaming} />
        </div>
      </main>

      <aside className="hidden w-72 shrink-0 overflow-y-auto border-l border-border lg:block">
        <SourcePanel
          sources={focusedMessage?.sources ?? []}
          repository={repository}
          activeRank={focus?.messageId === focusedMessage?.clientKey ? (focus?.rank ?? null) : null}
        />
      </aside>
    </div>
  );
}

function EmptyState({
  repositoryName,
  onAsk,
}: {
  repositoryName: string;
  onAsk: (query: string) => void;
}) {
  const examples = [
    "Explain the authentication flow.",
    "Where is payment processing implemented?",
    "Which services depend on UserService?",
    "How does refresh token rotation work?",
  ];
  return (
    <div className="mx-auto flex h-full max-w-lg flex-col items-center justify-center gap-4 text-center">
      <div className="flex size-10 items-center justify-center rounded-full bg-muted">
        <MessageSquareIcon className="size-5 text-muted-foreground" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">Ask about {repositoryName}</p>
        <p className="text-sm text-muted-foreground">
          Grounded in the indexed code — symbols, files, and dependencies.
        </p>
      </div>
      <div className="grid w-full gap-1.5">
        {examples.map((example) => (
          <button
            key={example}
            type="button"
            onClick={() => onAsk(example)}
            className="rounded-lg border border-border px-3 py-2 text-left text-sm text-muted-foreground hover:border-brand/30 hover:bg-muted/50 hover:text-foreground"
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}
