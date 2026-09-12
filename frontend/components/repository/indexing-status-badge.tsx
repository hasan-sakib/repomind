import { Badge } from "@/components/ui/badge";
import { INDEXING_JOB_STATUS_LABELS, type IndexingJobStatus } from "@/lib/types";
import { cn } from "cn";

const VARIANT: Record<IndexingJobStatus, "success" | "brand" | "destructive" | "warning" | "outline"> = {
  queued: "outline",
  running: "brand",
  succeeded: "success",
  partial: "warning",
  failed: "destructive",
};

export function IndexingStatusBadge({
  status,
  className,
}: {
  status: IndexingJobStatus;
  className?: string;
}) {
  return (
    <Badge variant={VARIANT[status]} className={cn(className)}>
      {(status === "running" || status === "queued") && (
        <span className="mr-0.5 size-1.5 animate-pulse rounded-full bg-current" />
      )}
      {INDEXING_JOB_STATUS_LABELS[status]}
    </Badge>
  );
}
