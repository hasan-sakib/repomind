import { KeyRoundIcon } from "lucide-react";

import { Button } from "@/components/ui/button";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function GitHubContinueLink() {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <div className="h-px flex-1 bg-border" />
        or
        <div className="h-px flex-1 bg-border" />
      </div>
      <Button
        variant="outline"
        className="w-full"
        render={<a href={`${API_BASE_URL}/api/v1/auth/github/login`} />}
      >
        <KeyRoundIcon className="size-4" />
        Continue with GitHub
      </Button>
    </div>
  );
}
