import { FolderGitIcon, PlusIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/empty-state";
import { StatusDot } from "@/components/shell/status-dot";
import { demoRepositories, repositoryStatusLabel, type RepositoryStatus } from "@/lib/demo-data";

const STATUS_BADGE_VARIANT: Record<
  RepositoryStatus,
  "success" | "brand" | "destructive" | "outline"
> = {
  ready: "success",
  indexing: "brand",
  failed: "destructive",
  pending: "outline",
};

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function RepositoriesPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Repositories</h1>
          <p className="text-sm text-muted-foreground">Connected repositories in this workspace.</p>
        </div>
        <Button disabled>
          <PlusIcon className="size-4" />
          Connect repository
        </Button>
      </div>

      {demoRepositories.length === 0 ? (
        <EmptyState
          icon={FolderGitIcon}
          title="No repositories connected"
          description="Install the RepoMind GitHub App and connect a repository to start asking questions about your codebase."
          action={
            <Button disabled>
              <PlusIcon className="size-4" />
              Connect repository
            </Button>
          }
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Repository</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Default branch</TableHead>
                <TableHead>Last indexed</TableHead>
                <TableHead>Connected</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {demoRepositories.map((repo) => (
                <TableRow key={repo.id}>
                  <TableCell className="font-medium text-foreground">
                    <span className="flex items-center gap-2">
                      <StatusDot status={repo.status} />
                      {repo.fullName}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Badge variant={STATUS_BADGE_VARIANT[repo.status]}>
                      {repositoryStatusLabel[repo.status]}
                    </Badge>
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {repo.defaultBranch}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDate(repo.lastIndexedAt)}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatDate(repo.connectedAt)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
