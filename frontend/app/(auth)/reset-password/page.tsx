"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { AuthCard } from "@/components/auth/auth-card";
import { FieldError } from "@/components/auth/field-error";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api-client";
import { confirmPasswordReset } from "@/lib/api/auth";
import { resetPasswordSchema } from "@/lib/validation/auth";

function ResetPasswordForm() {
  const token = useSearchParams().get("token");
  const [password, setPassword] = useState("");
  const [fieldError, setFieldError] = useState<string | undefined>();
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  if (!token) {
    return (
      <AuthCard title="Invalid link">
        <p className="text-sm text-muted-foreground">
          This password reset link is missing its token. Request a new one from the{" "}
          <Link href="/forgot-password" className="font-medium text-foreground hover:text-brand">
            forgot password
          </Link>{" "}
          page.
        </p>
      </AuthCard>
    );
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);
    const result = resetPasswordSchema.safeParse({ new_password: password });
    if (!result.success) {
      setFieldError(result.error.issues[0]?.message);
      return;
    }
    setFieldError(undefined);
    setSubmitting(true);
    try {
      await confirmPasswordReset({
        token: token as string,
        new_password: result.data.new_password,
      });
      setDone(true);
    } catch (error) {
      if (error instanceof ApiError && error.code === "invalid_or_expired_token") {
        setFormError("This reset link is invalid or has expired. Request a new one.");
      } else {
        setFormError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <AuthCard title="Password updated">
        <p className="mb-4 text-sm text-muted-foreground">
          Your password has been changed. Every other session has been signed out for security.
        </p>
        <Button className="w-full" render={<Link href="/login" />}>
          Sign in
        </Button>
      </AuthCard>
    );
  }

  return (
    <AuthCard title="Choose a new password">
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        <div className="space-y-1.5">
          <Label htmlFor="new_password">New password</Label>
          <Input
            id="new_password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-invalid={!!fieldError}
          />
          <FieldError message={fieldError} />
        </div>
        <FieldError message={formError ?? undefined} />
        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? "Updating…" : "Update password"}
        </Button>
      </form>
    </AuthCard>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordForm />
    </Suspense>
  );
}
