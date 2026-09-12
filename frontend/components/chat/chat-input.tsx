"use client";

import { useRef, useState } from "react";
import { SendIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export function ChatInput({
  onSubmit,
  disabled,
}: {
  onSubmit: (query: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
    textareaRef.current?.focus();
  };

  return (
    <div className="flex items-end gap-2 border-t border-border p-3">
      <Textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        placeholder="Ask about this codebase…"
        rows={1}
        className="max-h-40 resize-none"
        disabled={disabled}
      />
      <Button size="icon" onClick={submit} disabled={disabled || !value.trim()} aria-label="Send">
        <SendIcon className="size-4" />
      </Button>
    </div>
  );
}
