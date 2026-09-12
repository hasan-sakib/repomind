"use client";

import { useEffect, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useInvalidateMe, useMeQuery } from "@/hooks/use-me";
import { requestEmailVerification } from "@/lib/api/auth";
import { updateOrganization } from "@/lib/api/organizations";
import { ROLE_LABELS, roleAtLeast } from "@/lib/types";
import { useCurrentOrg } from "@/lib/current-org";

export default function GeneralSettingsPage() {
  const { data } = useMeQuery();
  const { currentOrg } = useCurrentOrg();
  const invalidateMe = useInvalidateMe();
  const [resendState, setResendState] = useState<"idle" | "sending" | "sent">("idle");
  const [name, setName] = useState(currentOrg?.organization.name ?? "");

  const renameMutation = useMutation({
    mutationFn: (nextName: string) =>
      updateOrganization(currentOrg?.organization.id as string, nextName),
    onSuccess: () => invalidateMe(),
  });

  // Keeps the input in sync with the server's name — on first load (in
  // case `currentOrg` wasn't ready yet when useState's initializer ran)
  // and after a successful rename refetches it.
  useEffect(() => {
    if (currentOrg) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setName(currentOrg.organization.name);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentOrg?.organization.name]);

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
  const trimmedName = name.trim();
  const canSubmitRename =
    canRenameOrg && trimmedName.length > 0 && trimmedName !== currentOrg.organization.name;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Organization</CardTitle>
          <CardDescription>
            {ROLE_LABELS[currentOrg.role]}
            {!canRenameOrg && " · renaming requires admin"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="flex max-w-sm items-end gap-2"
            onSubmit={(event) => {
              event.preventDefault();
              if (canSubmitRename) renameMutation.mutate(trimmedName);
            }}
          >
            <div className="flex-1 space-y-1.5">
              <label htmlFor="org-name" className="text-xs text-muted-foreground">
                Name
              </label>
              <Input
                id="org-name"
                value={name}
                disabled={!canRenameOrg}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <Button type="submit" size="sm" disabled={!canSubmitRename || renameMutation.isPending}>
              {renameMutation.isPending ? "Saving…" : "Save"}
            </Button>
          </form>
          <p className="mt-2 text-xs text-muted-foreground">
            Slug: <span className="font-mono">{currentOrg.organization.slug}</span> (not editable)
          </p>
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
