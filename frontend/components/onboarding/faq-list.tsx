import { FileChip } from "@/components/file-chip";
import type { FaqEntry, Repository } from "@/lib/types";

export function FaqList({
  entries,
  repository,
  gitRef,
}: {
  entries: FaqEntry[];
  repository: Repository;
  gitRef: string;
}) {
  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground">No FAQ entries were generated.</p>;
  }
  return (
    <ul className="space-y-3">
      {entries.map((entry, i) => (
        <li key={i} className="rounded-lg border border-border p-3">
          <p className="text-sm font-medium text-foreground">{entry.question}</p>
          <p className="mt-1 text-sm text-muted-foreground">{entry.answer}</p>
          {entry.file_paths.length > 0 && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {entry.file_paths.map((path) => (
                <FileChip key={path} path={path} repository={repository} gitRef={gitRef} />
              ))}
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}
