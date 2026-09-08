"use client";

import { use } from "react";

import { ChatShell } from "@/components/chat/chat-shell";

export default function NewChatPage({
  params,
}: {
  params: Promise<{ repositoryId: string }>;
}) {
  const { repositoryId } = use(params);
  return <ChatShell repositoryId={repositoryId} conversationId={null} />;
}
