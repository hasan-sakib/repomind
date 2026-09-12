"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { AuthCard } from "@/components/auth/auth-card";
import { Button } from "@/components/ui/button";
import { ApiError } from "@/lib/api-client";
import { confirmEmailVerification } from "@/lib/api/auth";

type Status = "verifying" | "success" | "error";

function VerifyEmailContent() {
  const token = useSearchParams().get("token");
  const [status, setStatus] = useState<Status>(token ? "verifying" : "error");

  useEffect(() => {
    if (!token) return;
    confirmEmailVerification(token)
      .then(() => setStatus("success"))
      .catch((error: unknown) => {
        if (error instanceof ApiError) {
          setStatus("error");
        }
      });
  }, [token]);

  if (status === "verifying") {
    return (
      <AuthCard title="Verifying your email">
        <p className="text-sm text-muted-foreground">One moment…</p>
      </AuthCard>
    );
  }

  if (status === "error") {
    return (
      <AuthCard title="Verification link invalid">
        <p className="mb-4 text-sm text-muted-foreground">
          This link is invalid or has expired. You can request a new one from your account settings
          once signed in.
        </p>
        <Button className="w-full" render={<Link href="/dashboard" />}>
          Go to dashboard
        </Button>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Email verified">
      <p className="mb-4 text-sm text-muted-foreground">Your email address is now verified.</p>
      <Button className="w-full" render={<Link href="/dashboard" />}>
        Go to dashboard
      </Button>
    </AuthCard>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={null}>
      <VerifyEmailContent />
    </Suspense>
  );
}
