"use client";

import { AppShell } from "@/components/shell/app-shell";
import { useMeQuery } from "@/hooks/use-me";
import { CurrentOrgProvider } from "@/lib/current-org";
import type { MeResponse } from "@/lib/types";

export function DashboardShellClient({
  initialMe,
  children,
}: {
  initialMe: MeResponse;
  children: React.ReactNode;
}) {
  const { data } = useMeQuery(initialMe);
  const organizations = data?.organizations ?? initialMe.organizations;

  return (
    <CurrentOrgProvider organizations={organizations}>
      <AppShell>{children}</AppShell>
    </CurrentOrgProvider>
  );
}
