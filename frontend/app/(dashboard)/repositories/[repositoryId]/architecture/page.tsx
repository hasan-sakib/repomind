"use client";

import { use } from "react";
import { NetworkIcon } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

import { ArchitectureExplorer } from "@/components/architecture/architecture-explorer";
import { getRepositoryOverview } from "@/lib/api/repositories";

export default function ArchitecturePage({
  params,
}: {
  params: Promise<{ repositoryId: string }>;
}) {
  const { repositoryId } = use(params);

  const overviewQuery = useQuery({
    queryKey: ["repository-overview", repositoryId],
    queryFn: () => getRepositoryOverview(repositoryId),
  });

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-2 border-b border-border px-4 py-2.5">
        <NetworkIcon className="size-3.5 text-muted-foreground" />
        <span className="truncate text-sm font-medium">
          {overviewQuery.data?.repository.full_name ?? "Architecture"}
        </span>
      </div>
      <div className="min-h-0 flex-1">
        <ArchitectureExplorer repositoryId={repositoryId} />
      </div>
    </div>
  );
}
