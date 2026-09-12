"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckIcon, CopyIcon, KeyIcon, PlusIcon, ShieldIcon } from "lucide-react";

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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { formatRelativeTime } from "@/lib/format-time";
import { createApiKey, getAuditLogs, listApiKeys, revokeApiKey } from "@/lib/api/organizations";
import { useCurrentOrg } from "@/lib/current-org";
import { ROLE_LABELS, roleAtLeast, type ApiKey, type ApiKeyCreated, type Role } from "@/lib/types";

const ASSIGNABLE_ROLES: Role[] = ["admin", "developer", "viewer"];

export default function SecuritySettingsPage() {
  const { currentOrg } = useCurrentOrg();
  const orgId = currentOrg?.organization.id;
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [created, setCreated] = useState<ApiKeyCreated | null>(null);
  const [revokeTarget, setRevokeTarget] = useState<ApiKey | null>(null);

  const keysQuery = useQuery({
    queryKey: ["api-keys", orgId],
    queryFn: () => listApiKeys(orgId as string),
    enabled: !!orgId,
  });

  const auditQuery = useQuery({
    queryKey: ["audit-logs", orgId],
    queryFn: () => getAuditLogs(orgId as string),
    enabled: !!orgId && roleAtLeast(currentOrg?.role ?? "viewer", "admin"),
  });

  const revokeMutation = useMutation({
    mutationFn: (apiKeyId: string) => revokeApiKey(orgId as string, apiKeyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["api-keys", orgId] });
      setRevokeTarget(null);
    },
  });

  if (!currentOrg) return null;
  const canManage = roleAtLeast(currentOrg.role, "admin");

  if (!canManage) {
    return (
      <EmptyState
        icon={ShieldIcon}
        title="Admin access required"
        description="API keys and the audit log are only visible to organization admins and owners."
      />
    );
  }

  return (
    <div className="space-y-8">
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-foreground">API keys</h2>
            <p className="text-xs text-muted-foreground">
              Programmatic, organization-scoped credentials for read access to the API.
            </p>
          </div>
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <PlusIcon className="size-4" />
            Create key
          </Button>
        </div>

        {keysQuery.isPending && (
          <div className="space-y-2 rounded-lg border border-border p-3">
            {Array.from({ length: 2 }).map((_, i) => (
              <Skeleton key={i} className="h-10 w-full" />
            ))}
          </div>
        )}
        {keysQuery.isError && (
          <ErrorState description="Couldn't load API keys." onRetry={() => keysQuery.refetch()} />
        )}
        {keysQuery.data && keysQuery.data.length === 0 && (
          <EmptyState
            icon={KeyIcon}
            title="No API keys yet"
            description="Create one to authenticate scripts or CI jobs against this organization's repositories."
          />
        )}
        {keysQuery.data && keysQuery.data.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Key</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Last used</TableHead>
                  <TableHead className="w-16" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {keysQuery.data.map((key) => (
                  <TableRow key={key.id}>
                    <TableCell className="font-medium">{key.name}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {key.key_prefix}…
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{ROLE_LABELS[key.role]}</Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {key.revoked_at ? (
                        <Badge variant="destructive">Revoked</Badge>
                      ) : (
                        formatRelativeTime(key.last_used_at)
                      )}
                    </TableCell>
                    <TableCell>
                      {!key.revoked_at && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="text-destructive"
                          onClick={() => setRevokeTarget(key)}
                        >
                          Revoke
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </section>

      <section className="space-y-3">
        <div>
          <h2 className="text-sm font-semibold text-foreground">Audit log</h2>
          <p className="text-xs text-muted-foreground">
            Recent security-relevant activity in this organization.
          </p>
        </div>
        {auditQuery.isPending && (
          <div className="space-y-2 rounded-lg border border-border p-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        )}
        {auditQuery.isError && (
          <ErrorState description="Couldn't load the audit log." onRetry={() => auditQuery.refetch()} />
        )}
        {auditQuery.data && auditQuery.data.length === 0 && (
          <p className="rounded-lg border border-dashed border-border py-8 text-center text-sm text-muted-foreground">
            No activity recorded yet.
          </p>
        )}
        {auditQuery.data && auditQuery.data.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Action</TableHead>
                  <TableHead>Target</TableHead>
                  <TableHead>When</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {auditQuery.data.map((entry) => (
                  <TableRow key={entry.id}>
                    <TableCell className="font-mono text-xs">{entry.action}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {entry.target_type ? `${entry.target_type}:${entry.target_id}` : "—"}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {formatRelativeTime(entry.created_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </section>

      <CreateApiKeyDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        organizationId={orgId as string}
        onCreated={(key) => {
          queryClient.invalidateQueries({ queryKey: ["api-keys", orgId] });
          setCreated(key);
        }}
      />

      <RevealSecretDialog apiKey={created} onOpenChange={(open) => !open && setCreated(null)} />

      <AlertDialog open={!!revokeTarget} onOpenChange={(open) => !open && setRevokeTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Revoke &ldquo;{revokeTarget?.name}&rdquo;?</AlertDialogTitle>
            <AlertDialogDescription>
              Any script or client using this key will immediately lose access. This cannot be
              undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => revokeTarget && revokeMutation.mutate(revokeTarget.id)}
            >
              Revoke
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function CreateApiKeyDialog({
  open,
  onOpenChange,
  organizationId,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  organizationId: string;
  onCreated: (key: ApiKeyCreated) => void;
}) {
  const [name, setName] = useState("");
  const [role, setRole] = useState<Role>("viewer");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    try {
      const key = await createApiKey(organizationId, { name, role });
      onCreated(key);
      setName("");
      setRole("viewer");
      onOpenChange(false);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create API key</DialogTitle>
          <DialogDescription>
            The key acts at the role you choose here, capped at your own role.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="key-name">Name</Label>
            <Input
              id="key-name"
              placeholder="CI pipeline"
              value={name}
              onChange={(e) => setName(e.target.value)}
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
          <DialogFooter>
            <Button type="submit" disabled={submitting || !name.trim()}>
              {submitting ? "Creating…" : "Create key"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function RevealSecretDialog({
  apiKey,
  onOpenChange,
}: {
  apiKey: ApiKeyCreated | null;
  onOpenChange: (open: boolean) => void;
}) {
  const [copied, setCopied] = useState(false);

  function handleCopy() {
    if (!apiKey) return;
    void navigator.clipboard.writeText(apiKey.secret);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <Dialog open={!!apiKey} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Copy your new key now</DialogTitle>
          <DialogDescription>
            This is the only time the full key is shown. Store it somewhere safe.
          </DialogDescription>
        </DialogHeader>
        <div className="flex items-center gap-2 rounded-md border border-border bg-muted px-3 py-2">
          <code className="flex-1 truncate text-xs">{apiKey?.secret}</code>
          <Button size="icon-sm" variant="ghost" onClick={handleCopy} aria-label="Copy">
            {copied ? <CheckIcon className="size-3.5" /> : <CopyIcon className="size-3.5" />}
          </Button>
        </div>
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>Done</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
