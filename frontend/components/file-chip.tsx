import { buildBlobUrl } from "@/lib/github-url";
import type { Repository } from "@/lib/types";

/** A small clickable file-path chip linking to its GitHub blob view —
 * shared by PR analysis and onboarding, both of which cite real repo
 * files inline in AI-generated or deterministic content. */
export function FileChip({
  path,
  repository,
  gitRef,
  symbolName,
}: {
  path: string;
  repository: Repository;
  gitRef?: string;
  symbolName?: string | null;
}) {
  return (
    <a
      href={buildBlobUrl(repository, path, { ref: gitRef })}
      target="_blank"
      rel="noreferrer"
      className="inline-flex max-w-full items-center gap-1 truncate rounded-md border border-border bg-muted px-1.5 py-0.5 font-mono text-[11px] text-foreground hover:border-brand hover:text-brand"
      title={path}
    >
      <span className="truncate">{path}</span>
      {symbolName && <span className="shrink-0 text-muted-foreground">· {symbolName}</span>}
    </a>
  );
}
