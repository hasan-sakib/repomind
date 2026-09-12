import { redirect } from "next/navigation";

import { DashboardShellClient } from "@/components/shell/dashboard-shell-client";
import { ApiError } from "@/lib/api-client";
import { serverApiFetch } from "@/lib/server-api";
import type { MeResponse } from "@/lib/types";

export default async function DashboardLayout({ children }: { children: React.ReactNode }) {
  let me: MeResponse;
  try {
    me = await serverApiFetch<MeResponse>("/api/v1/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) {
      redirect("/login");
    }
    throw error;
  }

  return <DashboardShellClient initialMe={me}>{children}</DashboardShellClient>;
}
