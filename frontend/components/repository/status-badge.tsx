import { Badge } from "@/components/ui/badge";
import { REPOSITORY_STATUS_LABELS, type RepositoryStatus } from "@/lib/types";
import { cn } from "cn";

const VARIANT: Record<RepositoryStatus, "success" | "brand" | "destructive" | "outline"> = {
  ready: "success",
  syncing: "brand",
  error: "destructive",
  pending: "outline",
};

export function RepositoryStatusBadge({
  status,
  className,
}: {
  status: RepositoryStatus;
  className?: string;
}) {
  return (
    <Badge variant={VARIANT[status]} className={cn(className)}>
      {status === "syncing" && (
        <span className="mr-0.5 size-1.5 animate-pulse rounded-full bg-current" />
      )}
      {REPOSITORY_STATUS_LABELS[status]}
    </Badge>
  );
}
