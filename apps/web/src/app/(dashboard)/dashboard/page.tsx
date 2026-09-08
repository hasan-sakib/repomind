"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { FolderGitIcon, PlusIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { RepositoryStatusBadge } from "@/components/repositories/status-badge";
import { listRepositories } from "@/lib/api/repositories";
import { useCurrentOrg } from "@/lib/current-org";
import { formatRelativeTime } from "@/lib/format-time";

export default function DashboardPage() {
  const { currentOrg } = useCurrentOrg();
  const organizationId = currentOrg?.organization.id;

  const repositoriesQuery = useQuery({
    queryKey: ["repositories", organizationId],
    queryFn: () => listRepositories(organizationId as string),
    enabled: !!organizationId,
  });

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Repositories</h1>
          <p className="text-sm text-muted-foreground">
            Connected repositories in {currentOrg?.organization.name ?? "this organization"}.
          </p>
        </div>
        <Button size="sm" render={<Link href="/repositories/connect" />}>
          <PlusIcon className="size-4" />
          Connect repository
        </Button>
      </div>

      {repositoriesQuery.isPending && (
        <div className="space-y-2 rounded-lg border border-border p-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      )}

      {repositoriesQuery.isError && (
        <ErrorState
          description="Couldn't load repositories."
          onRetry={() => repositoriesQuery.refetch()}
        />
      )}

      {repositoriesQuery.data && repositoriesQuery.data.length === 0 && (
        <EmptyState
          icon={FolderGitIcon}
          title="No repositories connected"
          description="Install the RepoMind GitHub App and connect a repository to see its activity here."
          action={
            <Button render={<Link href="/repositories/connect" />}>
              <PlusIcon className="size-4" />
              Connect repository
            </Button>
          }
        />
      )}

      {repositoriesQuery.data && repositoriesQuery.data.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Repository</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Language</TableHead>
                <TableHead>Last sync</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {repositoriesQuery.data.map((repo) => (
                <TableRow key={repo.id}>
                  <TableCell className="font-medium">
                    <Link
                      href={`/repositories/${repo.id}`}
                      className="flex items-center gap-2 text-foreground hover:text-brand hover:underline"
                    >
                      {repo.full_name}
                      {repo.private && (
                        <Badge variant="outline" className="text-[10px]">
                          Private
                        </Badge>
                      )}
                    </Link>
                  </TableCell>
                  <TableCell>
                    <RepositoryStatusBadge status={repo.status} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">{repo.language ?? "—"}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {formatRelativeTime(repo.last_synced_at)}
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
