import { Badge } from "@/components/ui/badge";
import { PR_ANALYSIS_STATUS_LABELS, type PRAnalysisStatus } from "@/lib/types";
import { cn } from "cn";

const VARIANT: Record<PRAnalysisStatus, "success" | "brand" | "destructive" | "outline"> = {
  queued: "outline",
  running: "brand",
  succeeded: "success",
  failed: "destructive",
};

export function AnalysisStatusBadge({
  status,
  className,
}: {
  status: PRAnalysisStatus;
  className?: string;
}) {
  return (
    <Badge variant={VARIANT[status]} className={cn(className)}>
      {(status === "running" || status === "queued") && (
        <span className="mr-0.5 size-1.5 animate-pulse rounded-full bg-current" />
      )}
      {PR_ANALYSIS_STATUS_LABELS[status]}
    </Badge>
  );
}
