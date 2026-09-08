"use client";

import { useState } from "react";
import {
  CheckIcon,
  CopyIcon,
  Loader2Icon,
  RotateCcwIcon,
  ThumbsDownIcon,
  ThumbsUpIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { ChatMarkdown } from "@/components/chat/markdown";
import { cn } from "cn";
import { QUERY_INTENT_LABELS, type ChatMessage, type MessageFeedback } from "@/lib/types";

export function MessageItem({
  message,
  isStreaming,
  canRegenerate,
  onRegenerate,
  onFeedback,
  onCitationClick,
}: {
  message: ChatMessage;
  isStreaming: boolean;
  canRegenerate: boolean;
  onRegenerate: () => void;
  onFeedback: (feedback: MessageFeedback | null) => void;
  onCitationClick: (index: number) => void;
}) {
  const [copied, setCopied] = useState(false);

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-lg bg-muted px-3 py-2 text-sm text-foreground">
          {message.content}
        </div>
      </div>
    );
  }

  const handleCopy = () => {
    void navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="max-w-[85%]">
      {message.intent && (
        <p className="mb-1 text-[11px] text-muted-foreground">
          {QUERY_INTENT_LABELS[message.intent]}
        </p>
      )}
      {message.content ? (
        <ChatMarkdown content={message.content} onCitationClick={onCitationClick} />
      ) : isStreaming ? (
        <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
          <Loader2Icon className="size-3.5 animate-spin" />
          Thinking…
        </div>
      ) : null}

      {!isStreaming && message.content && (
        <div className="mt-1.5 flex items-center gap-1">
          <Tooltip>
            <TooltipTrigger
              render={
                <Button variant="ghost" size="icon-sm" onClick={handleCopy} aria-label="Copy">
                  {copied ? (
                    <CheckIcon className="size-3.5" />
                  ) : (
                    <CopyIcon className="size-3.5" />
                  )}
                </Button>
              }
            />
            <TooltipContent>{copied ? "Copied" : "Copy"}</TooltipContent>
          </Tooltip>

          {canRegenerate && (
            <Tooltip>
              <TooltipTrigger
                render={
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    onClick={onRegenerate}
                    aria-label="Regenerate"
                  >
                    <RotateCcwIcon className="size-3.5" />
                  </Button>
                }
              />
              <TooltipContent>Regenerate</TooltipContent>
            </Tooltip>
          )}

          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Good response"
                  onClick={() => onFeedback(message.feedback === "up" ? null : "up")}
                  className={cn(message.feedback === "up" && "text-success")}
                >
                  <ThumbsUpIcon className="size-3.5" />
                </Button>
              }
            />
            <TooltipContent>Good response</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label="Bad response"
                  onClick={() => onFeedback(message.feedback === "down" ? null : "down")}
                  className={cn(message.feedback === "down" && "text-destructive")}
                >
                  <ThumbsDownIcon className="size-3.5" />
                </Button>
              }
            />
            <TooltipContent>Bad response</TooltipContent>
          </Tooltip>
        </div>
      )}
    </div>
  );
}
