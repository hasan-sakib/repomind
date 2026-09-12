"use client";

import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useMeQuery } from "@/hooks/use-me";
import { requestEmailVerification } from "@/lib/api/auth";
import { ROLE_LABELS, roleAtLeast } from "@/lib/types";
import { useCurrentOrg } from "@/lib/current-org";

export default function GeneralSettingsPage() {
  const { data } = useMeQuery();
  const { currentOrg } = useCurrentOrg();
  const [resendState, setResendState] = useState<"idle" | "sending" | "sent">("idle");

  async function handleResendVerification() {
    setResendState("sending");
    try {
      await requestEmailVerification();
      setResendState("sent");
    } catch {
      setResendState("idle");
    }
  }

  if (!data || !currentOrg) {
    return null;
  }

  const canRenameOrg = roleAtLeast(currentOrg.role, "admin");

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Organization</CardTitle>
          <CardDescription>
            {currentOrg.organization.name} · {ROLE_LABELS[currentOrg.role]}
            {!canRenameOrg && " (read-only for your role)"}
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Organization name changes are not yet available in this phase.
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Account</CardTitle>
          <CardDescription>{data.user.full_name}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Email</span>
            <span className="flex items-center gap-2 text-foreground">
              {data.user.email}
              {data.user.email_verified ? (
                <Badge variant="success">Verified</Badge>
              ) : (
                <Badge variant="warning">Unverified</Badge>
              )}
            </span>
          </div>
          {!data.user.email_verified && (
            <div className="flex items-center justify-between">
              <p className="text-xs text-muted-foreground">
                {resendState === "sent"
                  ? "Verification email sent — check your inbox."
                  : "Verify your email to secure your account."}
              </p>
              <Button
                size="sm"
                variant="outline"
                disabled={resendState !== "idle"}
                onClick={handleResendVerification}
              >
                {resendState === "sending" ? "Sending…" : "Resend"}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
