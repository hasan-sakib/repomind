"use client";

import { useQuery } from "@tanstack/react-query";
import {
  ExternalLinkIcon,
  GitCommitHorizontalIcon,
  Maximize2Icon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { getFileDetail, getRecentChanges } from "@/lib/api/architecture";
import { formatRelativeTime } from "@/lib/format-time";
import { NODE_KIND_LABELS, type GraphNode, type NodeKind, type Repository } from "@/lib/types";
import { KIND_ICON } from "./node-kind-icon";

function blobUrl(repository: Repository, path: string): string {
  return `${repository.html_url}/blob/${repository.default_branch}/${path}`;
}

function DependencyList({
  title,
  items,
  repository,
}: {
  title: string;
  items: { file_id: string; path: string; matched_name: string }[];
  repository: Repository;
}) {
  if (items.length === 0) {
    return (
      <div>
        <p className="text-xs font-medium text-foreground">{title}</p>
        <p className="mt-1 text-xs text-muted-foreground">None found.</p>
      </div>
    );
  }
  return (
    <div>
      <p className="text-xs font-medium text-foreground">{title}</p>
      <ul className="mt-1 space-y-1">
        {items.map((item) => (
          <li key={item.file_id}>
            <a
              href={blobUrl(repository, item.path)}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 truncate font-mono text-xs text-muted-foreground hover:text-brand hover:underline"
              title={item.path}
            >
              <span className="truncate">{item.path}</span>
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function DetailPanel({
  node,
  repositoryId,
  repository,
  onExpandPackage,
}: {
  node: GraphNode | null;
  repositoryId: string;
  repository: Repository;
  onExpandPackage?: (packagePath: string) => void;
}) {
  const fileDetailQuery = useQuery({
    queryKey: ["architecture-file-detail", repositoryId, node?.file_id],
    queryFn: () => getFileDetail(repositoryId, node!.file_id!),
    enabled: node?.node_type === "file" && !!node.file_id,
  });

  const recentChangesQuery = useQuery({
    queryKey: ["architecture-recent-changes", repositoryId, node?.file_id],
    queryFn: () => getRecentChanges(repositoryId, node!.file_id!),
    enabled: node?.node_type === "file" && !!node.file_id,
  });

  if (!node) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 px-4 text-center">
        <p className="text-xs text-muted-foreground">
          Select a node to inspect its details.
        </p>
      </div>
    );
  }

  if (node.node_type === "database") {
    return (
      <div className="space-y-3 p-3">
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <KIND_ICON.database className="size-3.5" />
          <span className="text-[10px] font-medium tracking-wide uppercase">Database</span>
        </div>
        <p className="text-sm font-medium text-foreground">PostgreSQL</p>
        <p className="text-xs text-muted-foreground">
          A synthetic node representing the database. Any file classified as a repository or
          model is connected here.
        </p>
      </div>
    );
  }

  if (node.node_type === "package") {
    const kind = node.kind as NodeKind;
    const Icon = KIND_ICON[kind];
    return (
      <div className="space-y-3 p-3">
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Icon className="size-3.5" />
          <span className="text-[10px] font-medium tracking-wide uppercase">
            {NODE_KIND_LABELS[kind]}
          </span>
        </div>
        <p className="truncate font-mono text-sm font-medium text-foreground" title={node.path ?? undefined}>
          {node.path || "(root)"}
        </p>
        <p className="text-xs text-muted-foreground">
          {node.file_count} {node.file_count === 1 ? "file" : "files"}
        </p>
        {onExpandPackage && node.path !== null && (
          <Button size="sm" variant="outline" onClick={() => onExpandPackage(node.path!)}>
            <Maximize2Icon className="size-3.5" />
            Expand package
          </Button>
        )}
      </div>
    );
  }

  // node.node_type === "file"
  const kind = node.kind as NodeKind;
  const Icon = KIND_ICON[kind];
  return (
    <div className="space-y-4 p-3">
      <div>
        <div className="flex items-center gap-1.5 text-muted-foreground">
          <Icon className="size-3.5" />
          <span className="text-[10px] font-medium tracking-wide uppercase">
            {NODE_KIND_LABELS[kind]}
          </span>
          {node.path && (
            <a
              href={blobUrl(repository, node.path)}
              target="_blank"
              rel="noreferrer"
              className="ml-auto text-muted-foreground hover:text-foreground"
              aria-label="Open on GitHub"
            >
              <ExternalLinkIcon className="size-3.5" />
            </a>
          )}
        </div>
        <p className="mt-1 truncate font-mono text-sm font-medium text-foreground" title={node.path ?? undefined}>
          {node.path}
        </p>
        {node.language && (
          <Badge variant="outline" className="mt-1 text-[10px]">
            {node.language}
          </Badge>
        )}
      </div>

      {fileDetailQuery.isPending && (
        <div className="space-y-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      )}

      {fileDetailQuery.isError && (
        <p className="text-xs text-muted-foreground">Couldn&apos;t load this file&apos;s details.</p>
      )}

      {fileDetailQuery.data && (
        <>
          <div>
            <p className="text-xs font-medium text-foreground">Symbols</p>
            {fileDetailQuery.data.symbols.length === 0 ? (
              <p className="mt-1 text-xs text-muted-foreground">None found.</p>
            ) : (
              <ul className="mt-1 space-y-1">
                {fileDetailQuery.data.symbols.map((symbol) => (
                  <li key={symbol.id} className="text-xs">
                    <a
                      href={`${blobUrl(repository, node.path!)}#L${symbol.start_line}-L${symbol.end_line}`}
                      target="_blank"
                      rel="noreferrer"
                      className="font-mono text-foreground hover:text-brand hover:underline"
                    >
                      {symbol.name}
                    </a>
                    <span className="text-muted-foreground"> · {symbol.symbol_type}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <DependencyList
            title="Dependencies"
            items={fileDetailQuery.data.dependencies}
            repository={repository}
          />
          <DependencyList
            title="Dependents"
            items={fileDetailQuery.data.dependents}
            repository={repository}
          />
        </>
      )}

      <div>
        <p className="text-xs font-medium text-foreground">Recent changes</p>
        {recentChangesQuery.isPending && (
          <div className="mt-1 space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3" />
          </div>
        )}
        {recentChangesQuery.isError && (
          <p className="mt-1 text-xs text-muted-foreground">Couldn&apos;t load recent commits.</p>
        )}
        {recentChangesQuery.data && recentChangesQuery.data.length === 0 && (
          <p className="mt-1 text-xs text-muted-foreground">No recent commits found.</p>
        )}
        {recentChangesQuery.data && recentChangesQuery.data.length > 0 && (
          <ul className="mt-1 space-y-1.5">
            {recentChangesQuery.data.map((commit) => (
              <li key={commit.sha}>
                <a
                  href={commit.html_url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-start gap-1.5 text-xs text-muted-foreground hover:text-foreground"
                >
                  <GitCommitHorizontalIcon className="mt-0.5 size-3.5 shrink-0" />
                  <span className="min-w-0">
                    <span className="block truncate text-foreground">{commit.message}</span>
                    <span>
                      {commit.author_login ?? commit.author_name ?? "Unknown"} ·{" "}
                      {formatRelativeTime(commit.authored_at)}
                    </span>
                  </span>
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
