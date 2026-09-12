"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PlusIcon } from "lucide-react";

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
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ErrorState } from "@/components/error-state";
import { useMeQuery } from "@/hooks/use-me";
import { ApiError } from "@/lib/api-client";
import { addMember, listMembers, removeMember, updateMemberRole } from "@/lib/api/organizations";
import { useCurrentOrg } from "@/lib/current-org";
import { ROLE_LABELS, roleAtLeast, type Member, type Role } from "@/lib/types";

const ASSIGNABLE_ROLES: Role[] = ["admin", "developer", "viewer"];

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

export default function MembersPage() {
  const { currentOrg } = useCurrentOrg();
  const { data: me } = useMeQuery();
  const queryClient = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const [removeTarget, setRemoveTarget] = useState<Member | null>(null);

  const orgId = currentOrg?.organization.id;
  const membersQuery = useQuery({
    queryKey: ["members", orgId],
    queryFn: () => listMembers(orgId as string),
    enabled: !!orgId,
  });

  const roleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: Role }) =>
      updateMemberRole(orgId as string, userId, role),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["members", orgId] }),
  });

  const removeMutation = useMutation({
    mutationFn: (userId: string) => removeMember(orgId as string, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["members", orgId] });
      setRemoveTarget(null);
    },
  });

  if (!currentOrg || !me) return null;

  const canManage = roleAtLeast(currentOrg.role, "admin");

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          {membersQuery.data ? `${membersQuery.data.length} member(s)` : "Members"}
        </p>
        {canManage && (
          <Button size="sm" onClick={() => setAddOpen(true)}>
            <PlusIcon className="size-4" />
            Add member
          </Button>
        )}
      </div>

      {membersQuery.isPending && (
        <div className="space-y-2 rounded-lg border border-border p-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      )}

      {membersQuery.isError && (
        <ErrorState description="Couldn't load members." onRetry={() => membersQuery.refetch()} />
      )}

      {membersQuery.data && (
        <div className="overflow-x-auto rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Member</TableHead>
                <TableHead>Role</TableHead>
                <TableHead className="w-20" />
              </TableRow>
            </TableHeader>
            <TableBody>
              {membersQuery.data.map((member) => {
                const isSelf = member.user.id === me.user.id;
                const canEditRole =
                  canManage && (member.role !== "owner" || currentOrg.role === "owner");
                const canRemove =
                  isSelf || (canManage && (member.role !== "owner" || currentOrg.role === "owner"));

                return (
                  <TableRow key={member.user.id}>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Avatar className="size-6">
                          <AvatarFallback className="text-[10px]">
                            {initials(member.user.full_name)}
                          </AvatarFallback>
                        </Avatar>
                        <div>
                          <p className="text-sm font-medium text-foreground">
                            {member.user.full_name}
                            {isSelf && (
                              <span className="ml-1 text-xs text-muted-foreground">(you)</span>
                            )}
                          </p>
                          <p className="text-xs text-muted-foreground">{member.user.email}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      {canEditRole && member.role !== "owner" ? (
                        <Select
                          value={member.role}
                          onValueChange={(role) =>
                            roleMutation.mutate({ userId: member.user.id, role: role as Role })
                          }
                        >
                          <SelectTrigger className="h-7 w-32">
                            <SelectValue>{(value: Role) => ROLE_LABELS[value]}</SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            {ASSIGNABLE_ROLES.map((role) => (
                              <SelectItem key={role} value={role}>
                                {ROLE_LABELS[role]}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) : (
                        <Badge variant={member.role === "owner" ? "brand" : "outline"}>
                          {ROLE_LABELS[member.role]}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {canRemove && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-destructive"
                          onClick={() => setRemoveTarget(member)}
                        >
                          {isSelf ? "Leave" : "Remove"}
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}

      <AddMemberDialog
        open={addOpen}
        onOpenChange={setAddOpen}
        organizationId={orgId as string}
        onAdded={() => queryClient.invalidateQueries({ queryKey: ["members", orgId] })}
      />

      <AlertDialog open={!!removeTarget} onOpenChange={(open) => !open && setRemoveTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {removeTarget?.user.id === me.user.id ? "Leave organization?" : "Remove member?"}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {removeTarget?.user.id === me.user.id
                ? "You will lose access to this organization."
                : `${removeTarget?.user.full_name} will lose access to this organization.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => removeTarget && removeMutation.mutate(removeTarget.user.id)}
            >
              Confirm
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function AddMemberDialog({
  open,
  onOpenChange,
  organizationId,
  onAdded,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  organizationId: string;
  onAdded: () => void;
}) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("developer");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await addMember(organizationId, { email, role });
      onAdded();
      setEmail("");
      setRole("developer");
      onOpenChange(false);
    } catch (err) {
      if (err instanceof ApiError && err.code === "user_not_found") {
        setError("No registered user with that email. They need to sign up first.");
      } else if (err instanceof ApiError && err.code === "member_already_exists") {
        setError("That person is already a member.");
      } else if (err instanceof ApiError && err.code === "plan_limit_reached") {
        setError(err.message || "Your plan's member limit has been reached.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add member</DialogTitle>
          <DialogDescription>
            Add an existing RepoMind user to this organization by email.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="member-email">Email</Label>
            <Input
              id="member-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label>Role</Label>
            <Select value={role} onValueChange={(value) => setRole(value as Role)}>
              <SelectTrigger className="w-full">
                <SelectValue>{(value: Role) => ROLE_LABELS[value]}</SelectValue>
              </SelectTrigger>
              <SelectContent>
                {ASSIGNABLE_ROLES.map((r) => (
                  <SelectItem key={r} value={r}>
                    {ROLE_LABELS[r]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {error && (
            <p className="text-xs text-destructive" role="alert">
              {error}
            </p>
          )}
          <DialogFooter>
            <Button type="submit" disabled={submitting}>
              {submitting ? "Adding…" : "Add member"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
