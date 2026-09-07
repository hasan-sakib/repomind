import { KeyRoundIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

export default function LoginPage() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 px-4">
      <div className="space-y-1 text-center">
        <h1 className="text-lg font-semibold tracking-tight">Sign in to RepoMind</h1>
        <p className="text-sm text-muted-foreground">
          Connect a repository to ask grounded questions about your codebase.
        </p>
      </div>
      <Button size="lg" className="w-64" disabled>
        <KeyRoundIcon className="size-4" />
        Sign in with GitHub
      </Button>
      <p className="max-w-xs text-center text-xs text-muted-foreground">
        Authentication is not implemented yet — see docs/architecture/backend-architecture.md for
        the planned GitHub App login flow.
      </p>
    </div>
  );
}
