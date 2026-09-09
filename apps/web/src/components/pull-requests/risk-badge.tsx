import { AlertTriangleIcon, ShieldAlertIcon, ShieldCheckIcon, type LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { PR_RISK_LEVEL_LABELS, type PRRiskLevel } from "@/lib/types";
import { cn } from "cn";

const VARIANT: Record<PRRiskLevel, "success" | "warning" | "destructive"> = {
  low: "success",
  medium: "warning",
  high: "destructive",
};

const ICON: Record<PRRiskLevel, LucideIcon> = {
  low: ShieldCheckIcon,
  medium: ShieldAlertIcon,
  high: AlertTriangleIcon,
};

export function RiskBadge({ level, className }: { level: PRRiskLevel; className?: string }) {
  const Icon = ICON[level];
  return (
    <Badge variant={VARIANT[level]} className={cn(className)}>
      <Icon className="size-3" />
      {PR_RISK_LEVEL_LABELS[level]}
    </Badge>
  );
}
