"use client";

import { use } from "react";

import { ChatShell } from "@/components/chat/chat-shell";

export default function ConversationChatPage({
  params,
}: {
  params: Promise<{ repositoryId: string; conversationId: string }>;
}) {
  const { repositoryId, conversationId } = use(params);
  return <ChatShell repositoryId={repositoryId} conversationId={conversationId} />;
}
