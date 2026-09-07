"use client";

import { ErrorState } from "@/components/error-state";

export default function WorkspaceError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
      <ErrorState
        title="Couldn't load this workspace"
        description={error.message || "An unexpected error occurred."}
        onRetry={reset}
      />
    </div>
  );
}
