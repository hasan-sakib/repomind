import { SystemStatus } from "@/components/system-status";

export default function Home() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4">
      <h1 className="text-xl font-semibold tracking-tight">RepoMind</h1>
      <p className="text-sm text-muted-foreground">
        Foundation scaffold — application UI arrives in the next phase.
      </p>
      <SystemStatus />
    </div>
  );
}
