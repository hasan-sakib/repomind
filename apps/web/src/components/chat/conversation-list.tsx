import Link from "next/link";
import { PlusIcon } from "lucide-react";

import { cn } from "cn";
import { formatRelativeTime } from "@/lib/format-time";
import type { Conversation } from "@/lib/types";

export function ConversationList({
  repositoryId,
  conversations,
  activeConversationId,
}: {
  repositoryId: string;
  conversations: Conversation[];
  activeConversationId: string | null;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="p-2">
        <Link
          href={`/repositories/${repositoryId}/chat`}
          className="flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-sm text-foreground hover:bg-muted"
        >
          <PlusIcon className="size-3.5" />
          New conversation
        </Link>
      </div>
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {conversations.length === 0 ? (
          <p className="px-1 py-4 text-center text-xs text-muted-foreground">
            No conversations yet
          </p>
        ) : (
          <ul className="space-y-0.5">
            {conversations.map((c) => (
              <li key={c.id}>
                <Link
                  href={`/repositories/${repositoryId}/chat/${c.id}`}
                  className={cn(
                    "flex flex-col gap-0.5 rounded-lg px-2.5 py-1.5 text-sm",
                    c.id === activeConversationId
                      ? "bg-muted text-foreground"
                      : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
                  )}
                >
                  <span className="truncate">{c.title ?? "New conversation"}</span>
                  <span className="text-[11px] text-muted-foreground">
                    {formatRelativeTime(c.updated_at)}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
