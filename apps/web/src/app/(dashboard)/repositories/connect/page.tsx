"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { GitBranchIcon, KeyRoundIcon, LockIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { githubInstallUrl, listAvailableRepositories, listInstallations } from "@/lib/api/github";
import { connectRepository } from "@/lib/api/repositories";
import { useCurrentOrg } from "@/lib/current-org";

export default function ConnectRepositoryPage() {
  const { currentOrg } = useCurrentOrg();
  const organizationId = currentOrg?.organization.id;
  const router = useRouter();
  const queryClient = useQueryClient();
  const [connectingId, setConnectingId] = useState<number | null>(null);

  const installationsQuery = useQuery({
    queryKey: ["github-installations", organizationId],
    queryFn: () => listInstallations(organizationId as string),
    enabled: !!organizationId,
  });

  const installation = installationsQuery.data?.[0];

  const availableQuery = useQuery({
    queryKey: ["available-repositories", organizationId, installation?.id],
    queryFn: () => listAvailableRepositories(organizationId as string, installation!.id),
    enabled: !!organizationId && !!installation,
  });

  const connectMutation = useMutation({
    mutationFn: (repo: { github_repo_id: number; full_name: string }) =>
      connectRepository(organizationId as string, {
        installation_id: installation!.id,
        github_repo_id: repo.github_repo_id,
        full_name: repo.full_name,
      }),
    onSuccess: (repository) => {
      queryClient.invalidateQueries({ queryKey: ["repositories", organizationId] });
      router.push(`/repositories/${repository.id}`);
    },
    onSettled: () => setConnectingId(null),
  });

  return (
    <div className="mx-auto max-w-2xl px-4 py-6 sm:px-6">
      <div className="mb-6">
        <h1 className="text-lg font-semibold tracking-tight">Connect a repository</h1>
        <p className="text-sm text-muted-foreground">
          Install the RepoMind GitHub App, then choose which repositories to connect.
        </p>
      </div>

      {installationsQuery.isPending && <Skeleton className="h-24 w-full" />}

      {installationsQuery.isError && (
        <ErrorState
          description="Couldn't load GitHub installations."
          onRetry={() => installationsQuery.refetch()}
        />
      )}

      {installationsQuery.data && installationsQuery.data.length === 0 && organizationId && (
        <EmptyState
          icon={KeyRoundIcon}
          title="No GitHub App installation yet"
          description="Install the RepoMind GitHub App on your GitHub account or organization to see repositories here."
          action={
            <Button render={<a href={githubInstallUrl(organizationId)} />}>Connect GitHub</Button>
          }
        />
      )}

      {installation && (
        <div className="space-y-3">
          <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
            {installation.account_login}
          </p>

          {availableQuery.isPending && (
            <div className="space-y-2 rounded-lg border border-border p-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          )}

          {availableQuery.isError && (
            <ErrorState
              description="Couldn't load repositories from GitHub."
              onRetry={() => availableQuery.refetch()}
            />
          )}

          {availableQuery.data && availableQuery.data.length === 0 && (
            <EmptyState
              icon={GitBranchIcon}
              title="Every accessible repository is already connected"
              description="Grant the GitHub App access to more repositories from your GitHub settings to connect them here."
            />
          )}

          {availableQuery.data && availableQuery.data.length > 0 && (
            <ul className="divide-y divide-border rounded-lg border border-border">
              {availableQuery.data.map((repo) => (
                <li
                  key={repo.github_repo_id}
                  className="flex items-center justify-between gap-3 px-3 py-2.5"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    {repo.private && (
                      <LockIcon className="size-3.5 shrink-0 text-muted-foreground" />
                    )}
                    <div className="min-w-0">
                      <p className="truncate text-sm font-medium text-foreground">
                        {repo.full_name}
                      </p>
                      {repo.description && (
                        <p className="truncate text-xs text-muted-foreground">{repo.description}</p>
                      )}
                    </div>
                  </div>
                  <Button
                    size="sm"
                    disabled={connectMutation.isPending}
                    onClick={() => {
                      setConnectingId(repo.github_repo_id);
                      connectMutation.mutate(repo);
                    }}
                  >
                    {connectMutation.isPending && connectingId === repo.github_repo_id
                      ? "Connecting…"
                      : "Connect"}
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <p className="mt-6 text-center text-sm text-muted-foreground">
        <Link href="/dashboard" className="hover:text-foreground">
          Back to repositories
        </Link>
      </p>
    </div>
  );
}
