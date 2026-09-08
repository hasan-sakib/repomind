"use client";

import { ROLE_LABELS } from "@/lib/types";
import { useCurrentOrg } from "@/lib/current-org";

export default function DashboardPage() {
  const { currentOrg } = useCurrentOrg();

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold tracking-tight">
          {currentOrg?.organization.name ?? "Dashboard"}
        </h1>
        <p className="text-sm text-muted-foreground">
          {currentOrg
            ? `You're signed in as ${ROLE_LABELS[currentOrg.role]}.`
            : "Loading your organization…"}
        </p>
      </div>
      <div className="rounded-lg border border-dashed border-border px-6 py-16 text-center">
        <p className="text-sm text-muted-foreground">
          Repository connection and AI chat land in the next phase. This phase is the authentication
          and multi-tenant foundation — see docs/product/PRD.md for scope.
        </p>
      </div>
    </div>
  );
}
