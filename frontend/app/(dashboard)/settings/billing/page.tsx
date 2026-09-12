"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { getBillingInfo, setPlan } from "@/lib/api/organizations";
import { useCurrentOrg } from "@/lib/current-org";
import type { Plan } from "@/lib/types";

const PLAN_ORDER: Plan[] = ["free", "pro", "team"];

function formatLimit(value: number | null, noun: string): string {
  return value === null ? `Unlimited ${noun}` : `${value} ${noun}`;
}

export default function BillingSettingsPage() {
  const { currentOrg } = useCurrentOrg();
  const orgId = currentOrg?.organization.id;
  const queryClient = useQueryClient();

  const billingQuery = useQuery({
    queryKey: ["billing", orgId],
    queryFn: () => getBillingInfo(orgId as string),
    enabled: !!orgId,
  });

  const planMutation = useMutation({
    mutationFn: (plan: Plan) => setPlan(orgId as string, plan),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["billing", orgId] });
      queryClient.invalidateQueries({ queryKey: ["usage", orgId] });
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });

  if (!currentOrg) return null;
  const isOwner = currentOrg.role === "owner";

  if (billingQuery.isPending) {
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-56 w-full" />
        ))}
      </div>
    );
  }

  if (billingQuery.isError) {
    return (
      <ErrorState description="Couldn't load billing info." onRetry={() => billingQuery.refetch()} />
    );
  }

  const billing = billingQuery.data;
  const plansByKey = Object.fromEntries(billing.plans.map((p) => [p.plan, p]));

  return (
    <div className="space-y-4">
      {!billing.is_billing_configured && (
        <div className="rounded-lg border border-warning/30 bg-warning/5 px-3 py-2 text-xs text-warning-foreground">
          No payment provider is connected yet, so plan changes here take effect immediately and
          free of charge — this is a temporary stand-in for real billing, available only to the
          organization owner.
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {PLAN_ORDER.map((plan) => {
          const entry = plansByKey[plan];
          if (!entry) return null;
          const isCurrent = billing.current_plan === plan;
          return (
            <Card key={plan} className={isCurrent ? "border-brand" : undefined}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm">{entry.label}</CardTitle>
                  {isCurrent && <Badge variant="brand">Current</Badge>}
                </div>
                <CardDescription className="space-y-1 pt-1">
                  <span className="block">
                    {formatLimit(entry.limits.max_repositories, "repositories")}
                  </span>
                  <span className="block">{formatLimit(entry.limits.max_members, "members")}</span>
                </CardDescription>
              </CardHeader>
              <CardContent>
                {isCurrent ? (
                  <Button size="sm" variant="outline" disabled className="w-full">
                    <CheckIcon className="size-3.5" />
                    Active plan
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    variant="outline"
                    className="w-full"
                    disabled={!isOwner || planMutation.isPending}
                    onClick={() => planMutation.mutate(plan)}
                  >
                    {planMutation.isPending && planMutation.variables === plan
                      ? "Switching…"
                      : `Switch to ${entry.label}`}
                  </Button>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {!isOwner && (
        <p className="text-xs text-muted-foreground">
          Only the organization owner can change plans.
        </p>
      )}
    </div>
  );
}
