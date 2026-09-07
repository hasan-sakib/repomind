import Link from "next/link";

import { SystemStatus } from "@/components/system-status";
import { Button } from "@/components/ui/button";
import { demoWorkspaces } from "@/lib/demo-data";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4">
      <h1 className="text-xl font-semibold tracking-tight">RepoMind</h1>
      <p className="max-w-sm text-center text-sm text-muted-foreground">
        Application shell preview — real auth and data land in the next phase.
      </p>
      <SystemStatus />
      <div className="mt-2 flex gap-2">
        <Button render={<Link href="/login" />} variant="outline">
          Sign in
        </Button>
        <Button render={<Link href={`/${demoWorkspaces[0].slug}`} />}>View shell demo</Button>
      </div>
    </div>
  );
}
