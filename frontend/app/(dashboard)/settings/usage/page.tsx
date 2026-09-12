"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { ErrorState } from "@/components/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { getUsageSummary } from "@/lib/api/organizations";
import { useCurrentOrg } from "@/lib/current-org";
import { PLAN_LABELS } from "@/lib/types";

function QuotaCard({ label, used, limit }: { label: string; used: number; limit: number | null }) {
  const percent = limit === null ? 0 : Math.min(100, (used / Math.max(limit, 1)) * 100);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{label}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        <p className="text-2xl font-semibold text-foreground">
          {used}
          <span className="text-sm font-normal text-muted-foreground">
            {" "}
            / {limit === null ? "Unlimited" : limit}
          </span>
        </p>
        {limit !== null && <Progress value={percent} />}
      </CardContent>
    </Card>
  );
}

function StatCard({ label, value }: { label: string; value: number }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-2xl font-semibold text-foreground">{value.toLocaleString()}</p>
      </CardContent>
    </Card>
  );
}

export default function UsageSettingsPage() {
  const { currentOrg } = useCurrentOrg();
  const orgId = currentOrg?.organization.id;

  const usageQuery = useQuery({
    queryKey: ["usage", orgId],
    queryFn: () => getUsageSummary(orgId as string),
    enabled: !!orgId,
  });

  if (!currentOrg) return null;

  if (usageQuery.isPending) {
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-28 w-full" />
        ))}
      </div>
    );
  }

  if (usageQuery.isError) {
    return (
      <ErrorState description="Couldn't load usage." onRetry={() => usageQuery.refetch()} />
    );
  }

  const usage = usageQuery.data;

  return (
    <div className="space-y-6">
      <p className="text-sm text-muted-foreground">
        Current plan: <span className="font-medium text-foreground">{PLAN_LABELS[usage.plan]}</span>
        . See{" "}
        <Link href="/settings/billing" className="underline">
          Billing
        </Link>{" "}
        to change it.
      </p>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-foreground">Plan quotas</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <QuotaCard
            label="Repositories"
            used={usage.repositories_used}
            limit={usage.limits.max_repositories}
          />
          <QuotaCard label="Members" used={usage.members_used} limit={usage.limits.max_members} />
        </div>
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-foreground">Activity</h2>
        <p className="mb-3 text-xs text-muted-foreground">
          Not plan-limited today — shown for visibility into what this organization actually uses.
        </p>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <StatCard label="AI tokens used" value={usage.ai_tokens_used} />
          <StatCard label="Indexing runs" value={usage.indexing_runs} />
          <StatCard label="PR analyses" value={usage.pr_analyses_run} />
          <StatCard label="Onboarding guides" value={usage.onboarding_guides_generated} />
          <StatCard label="Analytics snapshots" value={usage.analytics_snapshots_generated} />
        </div>
      </div>
    </div>
  );
}
