"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronRightIcon, FolderTreeIcon, SearchIcon, XIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { getModuleGraph, getPackageGraph, searchArchitecture } from "@/lib/api/architecture";
import { getRepositoryOverview } from "@/lib/api/repositories";
import { NODE_KIND_LABELS, type ArchitectureSearchResult, type GraphNode, type NodeKind } from "@/lib/types";
import { DependencyGraph } from "./dependency-graph";
import { DetailPanel } from "./detail-panel";
import { KIND_ICON } from "./node-kind-icon";

const ALL_KINDS: (NodeKind | "database")[] = [
  "route",
  "service",
  "repository",
  "model",
  "schema",
  "other",
  "database",
];

export function ArchitectureExplorer({ repositoryId }: { repositoryId: string }) {
  const [currentPackage, setCurrentPackage] = useState<string | null>(null);
  const [clickedNode, setClickedNode] = useState<GraphNode | null>(null);
  // Set when a search result jump lands on a package whose graph hasn't
  // loaded yet — resolved against `graphQuery.data` during render below,
  // once the module graph for that package finishes fetching.
  const [pendingFileId, setPendingFileId] = useState<string | null>(null);
  const [activeKinds, setActiveKinds] = useState<Set<NodeKind | "database">>(
    new Set(ALL_KINDS),
  );
  const [searchTerm, setSearchTerm] = useState("");
  const [searchOpen, setSearchOpen] = useState(false);

  const repositoryQuery = useQuery({
    queryKey: ["repository-overview", repositoryId],
    queryFn: () => getRepositoryOverview(repositoryId),
  });

  const graphQuery = useQuery({
    queryKey: ["architecture-graph", repositoryId, currentPackage],
    queryFn: () =>
      currentPackage === null
        ? getPackageGraph(repositoryId)
        : getModuleGraph(repositoryId, currentPackage),
  });

  const searchQuery = useQuery({
    queryKey: ["architecture-search", repositoryId, searchTerm],
    queryFn: () => searchArchitecture(repositoryId, searchTerm),
    enabled: searchTerm.trim().length > 1,
  });

  const pendingMatch =
    pendingFileId != null
      ? (graphQuery.data?.nodes.find((n) => n.file_id === pendingFileId) ?? null)
      : null;
  const selectedNode = pendingMatch ?? clickedNode;

  const visibleKinds = useMemo(() => {
    const kinds = new Set<NodeKind | "database">();
    for (const node of graphQuery.data?.nodes ?? []) kinds.add(node.kind);
    return ALL_KINDS.filter((kind) => kinds.has(kind));
  }, [graphQuery.data]);

  const { filteredNodes, filteredEdges } = useMemo(() => {
    const nodes = graphQuery.data?.nodes ?? [];
    const edges = graphQuery.data?.edges ?? [];
    if (activeKinds.size === ALL_KINDS.length) {
      return { filteredNodes: nodes, filteredEdges: edges };
    }
    const visibleIds = new Set(
      nodes.filter((n) => activeKinds.has(n.kind)).map((n) => n.id),
    );
    return {
      filteredNodes: nodes.filter((n) => visibleIds.has(n.id)),
      filteredEdges: edges.filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target)),
    };
  }, [graphQuery.data, activeKinds]);

  function toggleKind(kind: NodeKind | "database") {
    setActiveKinds((prev) => {
      const next = new Set(prev);
      if (next.has(kind)) next.delete(kind);
      else next.add(kind);
      return next;
    });
  }

  function handleNodeClick(node: GraphNode) {
    setPendingFileId(null);
    setClickedNode(node);
  }

  function handleNodeDoubleClick(node: GraphNode) {
    if (node.node_type === "package" && node.path !== null) {
      setCurrentPackage(node.path);
      setPendingFileId(null);
      setClickedNode(null);
      setActiveKinds(new Set(ALL_KINDS));
    }
  }

  function handleSearchResultClick(result: ArchitectureSearchResult) {
    setSearchOpen(false);
    setSearchTerm("");
    if (result.package === currentPackage) {
      const match = graphQuery.data?.nodes.find((n) => n.file_id === result.file_id);
      setPendingFileId(null);
      setClickedNode(match ?? null);
    } else {
      setPendingFileId(result.file_id);
      setClickedNode(null);
      setCurrentPackage(result.package);
      setActiveKinds(new Set(ALL_KINDS));
    }
  }

  if (repositoryQuery.isPending || graphQuery.isPending) {
    return (
      <div className="grid h-full grid-cols-1 gap-3 p-3 md:grid-cols-[1fr_18rem]">
        <Skeleton className="h-full w-full" />
        <Skeleton className="hidden h-full w-full md:block" />
      </div>
    );
  }

  if (repositoryQuery.isError || graphQuery.isError) {
    return (
      <div className="flex h-full items-center justify-center p-4">
        <ErrorState
          title="Couldn't load the architecture graph"
          description="This repository may not be indexed yet, or the package no longer exists."
          onRetry={() => {
            repositoryQuery.refetch();
            graphQuery.refetch();
          }}
        />
      </div>
    );
  }

  if (graphQuery.data.nodes.length === 0 && currentPackage === null) {
    return (
      <div className="flex h-full items-center justify-center p-4">
        <EmptyState
          icon={FolderTreeIcon}
          title="Nothing to visualize yet"
          description="Index this repository to build its architecture graph."
        />
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center gap-2 border-b border-border px-3 py-2">
        <button
          type="button"
          onClick={() => {
            setCurrentPackage(null);
            setPendingFileId(null);
            setClickedNode(null);
            setActiveKinds(new Set(ALL_KINDS));
          }}
          className={
            currentPackage === null
              ? "text-sm font-medium text-foreground"
              : "text-sm text-muted-foreground hover:text-foreground"
          }
        >
          Packages
        </button>
        {currentPackage !== null && (
          <>
            <ChevronRightIcon className="size-3.5 shrink-0 text-muted-foreground" />
            <span className="truncate font-mono text-sm font-medium text-foreground">
              {currentPackage || "(root)"}
            </span>
          </>
        )}

        <div className="relative ml-auto min-w-0 flex-1 max-w-xs">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setSearchOpen(true);
            }}
            onFocus={() => setSearchOpen(true)}
            placeholder="Search files or symbols…"
            className="pl-7"
          />
          {searchTerm && (
            <button
              type="button"
              onClick={() => setSearchTerm("")}
              className="absolute top-1/2 right-2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              aria-label="Clear search"
            >
              <XIcon className="size-3.5" />
            </button>
          )}
          {searchOpen && searchTerm.trim().length > 1 && (
            <div className="absolute top-full right-0 left-0 z-10 mt-1 max-h-72 overflow-y-auto rounded-lg border border-border bg-popover shadow-md">
              {searchQuery.isPending && (
                <p className="p-3 text-xs text-muted-foreground">Searching…</p>
              )}
              {searchQuery.isError && (
                <p className="p-3 text-xs text-muted-foreground">Search failed.</p>
              )}
              {searchQuery.data && searchQuery.data.length === 0 && (
                <p className="p-3 text-xs text-muted-foreground">No matches.</p>
              )}
              {searchQuery.data?.map((result) => (
                <button
                  key={result.file_id}
                  type="button"
                  onClick={() => handleSearchResultClick(result)}
                  className="block w-full truncate px-3 py-2 text-left text-xs hover:bg-muted"
                >
                  <span className="font-mono text-foreground">{result.path}</span>
                  {result.matched_symbol_name && (
                    <span className="text-muted-foreground"> · {result.matched_symbol_name}</span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 border-b border-border px-3 py-2">
        {visibleKinds.map((kind) => {
          const Icon = KIND_ICON[kind];
          const active = activeKinds.has(kind);
          return (
            <Badge
              key={kind}
              variant={active ? "brand" : "outline"}
              className="cursor-pointer select-none"
              onClick={() => toggleKind(kind)}
            >
              <Icon className="size-3" />
              {kind === "database" ? "Database" : NODE_KIND_LABELS[kind]}
            </Badge>
          );
        })}
      </div>

      <div className="grid min-h-0 flex-1 grid-cols-1 md:grid-cols-[1fr_18rem]">
        <div className="min-h-0" onClick={() => setSearchOpen(false)}>
          <DependencyGraph
            nodes={filteredNodes}
            edges={filteredEdges}
            selectedNodeId={selectedNode?.id ?? null}
            onNodeClick={handleNodeClick}
            onNodeDoubleClick={handleNodeDoubleClick}
          />
        </div>
        <div className="hidden min-h-0 overflow-y-auto border-l border-border md:block">
          <DetailPanel
            node={selectedNode}
            repositoryId={repositoryId}
            repository={repositoryQuery.data.repository}
            onExpandPackage={(packagePath) => {
              setCurrentPackage(packagePath);
              setPendingFileId(null);
              setClickedNode(null);
              setActiveKinds(new Set(ALL_KINDS));
            }}
          />
        </div>
      </div>
    </div>
  );
}
