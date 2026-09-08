"use client";

import { useEffect, useRef } from "react";
import {
  ExternalLinkIcon,
  GitCommitHorizontalIcon,
  NetworkIcon,
  SearchIcon,
} from "lucide-react";

import { cn } from "cn";
import type { Repository, SourceReference } from "@/lib/types";

const SOURCE_TYPE_ICON = {
  vector: SearchIcon,
  dependency: NetworkIcon,
  git_history: GitCommitHorizontalIcon,
} as const;

const SOURCE_TYPE_LABEL = {
  vector: "Semantic match",
  dependency: "Dependency",
  git_history: "Commit",
} as const;

function sourceHref(source: SourceReference, repository: Repository): string | null {
  if (source.source_type === "git_history") return source.commit_url;
  if (!source.file_path) return null;
  const lines =
    source.start_line == null
      ? ""
      : source.start_line === source.end_line
        ? `#L${source.start_line}`
        : `#L${source.start_line}-L${source.end_line}`;
  return `${repository.html_url}/blob/${repository.default_branch}/${source.file_path}${lines}`;
}

export function SourcePanel({
  sources,
  repository,
  activeRank,
}: {
  sources: SourceReference[];
  repository: Repository;
  activeRank: number | null;
}) {
  const itemRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  useEffect(() => {
    if (activeRank == null) return;
    itemRefs.current.get(activeRank)?.scrollIntoView({ behavior: "smooth", block: "center" });
  }, [activeRank]);

  if (sources.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 px-4 text-center">
        <p className="text-xs text-muted-foreground">
          Sources for the assistant&apos;s answer will appear here.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2 p-3">
      {sources.map((source) => {
        const Icon = SOURCE_TYPE_ICON[source.source_type];
        const href = sourceHref(source, repository);
        const isActive = activeRank === source.rank;
        return (
          <div
            key={source.rank}
            ref={(el) => {
              if (el) itemRefs.current.set(source.rank, el);
            }}
            className={cn(
              "rounded-lg border px-3 py-2 text-xs transition-colors",
              isActive ? "border-brand bg-brand/5" : "border-border",
            )}
          >
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Icon className="size-3.5 shrink-0" />
              <span className="font-medium">{source.rank}</span>
              <span className="truncate">{SOURCE_TYPE_LABEL[source.source_type]}</span>
              {href && (
                <a
                  href={href}
                  target="_blank"
                  rel="noreferrer"
                  className="ml-auto shrink-0 text-muted-foreground hover:text-foreground"
                  aria-label="Open on GitHub"
                >
                  <ExternalLinkIcon className="size-3.5" />
                </a>
              )}
            </div>
            {source.file_path ? (
              <>
                <p className="mt-1 truncate font-mono text-foreground">{source.file_path}</p>
                {source.start_line != null && (
                  <p className="text-muted-foreground">
                    {source.start_line === source.end_line
                      ? `Line ${source.start_line}`
                      : `Lines ${source.start_line}-${source.end_line}`}
                    {source.symbol_name && <> · {source.symbol_name}</>}
                  </p>
                )}
              </>
            ) : (
              <p className="mt-1 font-mono text-foreground">
                {(source.commit_sha ?? "").slice(0, 7)}
              </p>
            )}
          </div>
        );
      })}
    </div>
  );
}
