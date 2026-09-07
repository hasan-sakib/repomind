import { cn } from "cn";

import type { RepositoryStatus } from "@/lib/demo-data";

const STATUS_DOT_CLASSES: Record<RepositoryStatus, string> = {
  pending: "bg-muted-foreground/40",
  indexing: "bg-brand animate-pulse",
  ready: "bg-success",
  failed: "bg-destructive",
};

export function StatusDot({ status }: { status: RepositoryStatus }) {
  return (
    <span
      className={cn("size-2 shrink-0 rounded-full", STATUS_DOT_CLASSES[status])}
      aria-hidden="true"
    />
  );
}
