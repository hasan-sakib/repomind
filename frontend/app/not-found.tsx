import Link from "next/link";

import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 px-4 py-16 text-center">
      <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
        404
      </p>
      <h1 className="text-xl font-semibold tracking-tight">Page not found</h1>
      <p className="max-w-sm text-sm text-muted-foreground">
        The page you&apos;re looking for doesn&apos;t exist, or you may not have access to it.
      </p>
      <Button render={<Link href="/dashboard" />}>Back to dashboard</Button>
    </div>
  );
}
