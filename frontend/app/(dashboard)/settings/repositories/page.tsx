"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { LockIcon, UsersIcon } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { listMembers } from "@/lib/api/organizations";
import {
  grantRepositoryAccess,
  listRepositories,
  listRepositoryMembers,
  revokeRepositoryAccess,
} from "@/lib/api/repositories";
import { useCurrentOrg } from "@/lib/current-org";
import { roleAtLeast, type Repository } from "@/lib/types";

function initials(name: string) {
  return (
    name
      .split(" ")
      .map((part) => part.charAt(0))
      .join("")
      .slice(0, 2)
      .toUpperCase() || "?"
  );
}

export default function RepositoryPermissionsPage() {
  const { currentOrg } = useCurrentOrg();
  const orgId = currentOrg?.organization.id;
  const [managing, setManaging] = useState<Repository | null>(null);

  const repositoriesQuery = useQuery({
    queryKey: ["repositories", orgId],
    queryFn: () => listRepositories(orgId as string),
    enabled: !!orgId,
  });

  if (!currentOrg) return null;
  const canManage = roleAtLeast(currentOrg.role, "admin");

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Every organization member gets access to a repository automatically when it&apos;s
        connected, or when they join. Use this to restrict or restore an individual member&apos;s
        access to a specific repository.
      </p>

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
          icon={LockIcon}
          title="No repositories connected"
          description="Connect a repository to manage who can see it."
        />
      )}

      {repositoriesQuery.data && repositoriesQuery.data.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Repository</TableHead>
                <TableHead className="w-32" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {repositoriesQuery.data.map((repo) => (
                <TableRow key={repo.id}>
                  <TableCell className="font-medium">
                    <div className="flex items-center gap-2">
                      {repo.full_name}
                      {repo.private && (
                        <Badge variant="outline" className="text-[10px]">
                          Private
                        </Badge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Button
                      size="sm"
                      variant="ghost"
                      disabled={!canManage}
                      onClick={() => setManaging(repo)}
                    >
                      <UsersIcon className="size-3.5" />
                      Manage access
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <ManageAccessDialog
        repository={managing}
        organizationId={orgId as string}
        onOpenChange={(open) => !open && setManaging(null)}
      />
    </div>
  );
}

function ManageAccessDialog({
  repository,
  organizationId,
  onOpenChange,
}: {
  repository: Repository | null;
  organizationId: string;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();

  const membersQuery = useQuery({
    queryKey: ["members", organizationId],
    queryFn: () => listMembers(organizationId),
    enabled: !!repository,
  });

  const repoMembersQuery = useQuery({
    queryKey: ["repository-members", repository?.id],
    queryFn: () => listRepositoryMembers(repository?.id as string),
    enabled: !!repository,
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["repository-members", repository?.id] });

  const grantMutation = useMutation({
    mutationFn: (userId: string) => grantRepositoryAccess(repository?.id as string, userId),
    onSuccess: invalidate,
  });
  const revokeMutation = useMutation({
    mutationFn: (userId: string) => revokeRepositoryAccess(repository?.id as string, userId),
    onSuccess: invalidate,
  });

  const accessibleIds = new Set(repoMembersQuery.data?.map((m) => m.user.id));

  return (
    <Dialog open={!!repository} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Manage access — {repository?.full_name}</DialogTitle>
          <DialogDescription>
            Toggle which organization members can see this repository.
          </DialogDescription>
        </DialogHeader>
        {(membersQuery.isPending || repoMembersQuery.isPending) && (
          <div className="space-y-2">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-9 w-full" />
            ))}
          </div>
        )}
        {membersQuery.data && repoMembersQuery.data && (
          <ul className="max-h-80 space-y-1 overflow-y-auto">
            {membersQuery.data.map((member) => {
              const hasAccess = accessibleIds.has(member.user.id);
              return (
                <li
                  key={member.user.id}
                  className="flex items-center justify-between gap-2 rounded-md px-2 py-1.5 hover:bg-muted"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    <Avatar className="size-6 shrink-0">
                      <AvatarFallback className="text-[10px]">
                        {initials(member.user.full_name)}
                      </AvatarFallback>
                    </Avatar>
                    <div className="min-w-0">
                      <p className="truncate text-sm text-foreground">{member.user.full_name}</p>
                      <p className="truncate text-xs text-muted-foreground">{member.user.email}</p>
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant={hasAccess ? "outline" : "default"}
                    disabled={grantMutation.isPending || revokeMutation.isPending}
                    onClick={() =>
                      hasAccess
                        ? revokeMutation.mutate(member.user.id)
                        : grantMutation.mutate(member.user.id)
                    }
                  >
                    {hasAccess ? "Revoke" : "Grant"}
                  </Button>
                </li>
              );
            })}
          </ul>
        )}
      </DialogContent>
    </Dialog>
  );
}
