"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { FolderGitIcon, SparklesIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
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
import { listRepositories } from "@/lib/api/repositories";
import { useCurrentOrg } from "@/lib/current-org";

export default function OnboardingRepositoryPickerPage() {
  const { currentOrg } = useCurrentOrg();
  const organizationId = currentOrg?.organization.id;

  const repositoriesQuery = useQuery({
    queryKey: ["repositories", organizationId],
    queryFn: () => listRepositories(organizationId as string),
    enabled: !!organizationId,
  });

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6">
      <div className="mb-4">
        <h1 className="text-lg font-semibold tracking-tight">Onboarding</h1>
        <p className="text-sm text-muted-foreground">
          A guided introduction to a repository — architecture, modules, setup, and a learning
          path — generated from its actual code.
        </p>
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
          description="Connect a repository to generate its onboarding guide."
        />
      )}

      {repositoriesQuery.data && repositoriesQuery.data.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Repository</TableHead>
                <TableHead>Language</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {repositoriesQuery.data.map((repo) => (
                <TableRow key={repo.id}>
                  <TableCell className="font-medium">
                    <Link
                      href={`/repositories/${repo.id}/onboarding`}
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
                  <TableCell className="text-muted-foreground">{repo.language ?? "—"}</TableCell>
                  <TableCell>
                    <Link
                      href={`/repositories/${repo.id}/onboarding`}
                      className="flex items-center justify-end gap-1 text-xs text-muted-foreground hover:text-foreground"
                    >
                      <SparklesIcon className="size-3.5" />
                      View guide
                    </Link>
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
