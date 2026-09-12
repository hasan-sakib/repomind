"use client";

import { use, useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/error-state";
import { RepositoryStatusBadge } from "@/components/repository/status-badge";
import { disconnectRepository, getRepositoryOverview } from "@/lib/api/repositories";
import { useCurrentOrg } from "@/lib/current-org";

export default function RepositorySettingsPage({
  params,
}: {
  params: Promise<{ repositoryId: string }>;
}) {
  const { repositoryId } = use(params);
  const { currentOrg } = useCurrentOrg();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [confirmOpen, setConfirmOpen] = useState(false);

  const overviewQuery = useQuery({
    queryKey: ["repository-overview", repositoryId],
    queryFn: () => getRepositoryOverview(repositoryId),
  });

  const disconnectMutation = useMutation({
    mutationFn: () => disconnectRepository(repositoryId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["repositories", currentOrg?.organization.id] });
      router.push("/dashboard");
    },
  });

  if (overviewQuery.isPending) {
    return (
      <div className="mx-auto max-w-2xl space-y-4 px-4 py-6 sm:px-6">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  if (overviewQuery.isError) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-6 sm:px-6">
        <ErrorState
          description="Couldn't load repository settings."
          onRetry={() => overviewQuery.refetch()}
        />
      </div>
    );
  }

  const { repository } = overviewQuery.data;

  return (
    <div className="mx-auto max-w-2xl space-y-4 px-4 py-6 sm:px-6">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">{repository.name} settings</h1>
        <p className="text-sm text-muted-foreground">{repository.full_name}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Sync status</CardTitle>
          <CardDescription>
            <RepositoryStatusBadge status={repository.status} />
          </CardDescription>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          Default branch: <span className="text-foreground">{repository.default_branch}</span>
        </CardContent>
      </Card>

      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="text-sm">Disconnect repository</CardTitle>
          <CardDescription>
            Removes all synced branches, commits, pull requests, and issues for this repository.
            This cannot be undone.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="destructive" onClick={() => setConfirmOpen(true)}>
            Disconnect repository
          </Button>
        </CardContent>
      </Card>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Disconnect {repository.full_name}?</AlertDialogTitle>
            <AlertDialogDescription>
              All synced data for this repository will be permanently deleted. RepoMind&apos;s
              GitHub App access to it is unaffected — you can reconnect it later.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => disconnectMutation.mutate()}>
              Disconnect
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
