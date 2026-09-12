"use client";

import { RefreshCwIcon, WifiIcon, WifiOffIcon } from "lucide-react";

import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useRealtime } from "@/lib/realtime-context";
import { cn } from "cn";

const LABEL = {
  connecting: "Connecting…",
  open: "Live updates connected",
  reconnecting: "Reconnecting…",
  closed: "Live updates disconnected",
} as const;

export function ConnectionStatus() {
  const { status } = useRealtime();

  return (
    <Tooltip>
      <TooltipTrigger
        render={
          <span
            className="flex size-7 items-center justify-center rounded-md"
            aria-label={LABEL[status]}
          >
            {status === "open" && <WifiIcon className="size-3.5 text-success" />}
            {(status === "connecting" || status === "reconnecting") && (
              <RefreshCwIcon className={cn("size-3.5 animate-spin text-muted-foreground")} />
            )}
            {status === "closed" && <WifiOffIcon className="size-3.5 text-destructive" />}
          </span>
        }
      />
      <TooltipContent>{LABEL[status]}</TooltipContent>
    </Tooltip>
  );
}
