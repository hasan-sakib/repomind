import {
  CheckCircle2Icon,
  ExternalLinkIcon,
  FileCodeIcon,
  FlaskConicalIcon,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { buildBlobUrl } from "@/lib/github-url";
import type { PullRequestAnalysis, Repository } from "@/lib/types";
import { RiskBadge } from "./risk-badge";

const FILE_STATUS_VARIANT: Record<string, "success" | "warning" | "destructive" | "outline"> = {
  added: "success",
  modified: "outline",
  removed: "destructive",
  renamed: "warning",
};

function FileLink({
  path,
  repository,
  headSha,
  symbolName,
}: {
  path: string;
  repository: Repository;
  headSha: string;
  symbolName?: string | null;
}) {
  return (
    <a
      href={buildBlobUrl(repository, path, { ref: headSha })}
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

export function AnalysisPanel({
  analysis,
  repository,
}: {
  analysis: PullRequestAnalysis;
  repository: Repository;
}) {
  const totals = analysis.files_analyzed.reduce(
    (acc, f) => ({ additions: acc.additions + f.additions, deletions: acc.deletions + f.deletions }),
    { additions: 0, deletions: 0 },
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center gap-2">
        {analysis.risk_level && <RiskBadge level={analysis.risk_level} />}
        <span className="text-xs text-muted-foreground">
          {analysis.files_analyzed.length}{" "}
          {analysis.files_analyzed.length === 1 ? "file" : "files"} changed · {" "}
          <span className="text-success">+{totals.additions}</span>{" "}
          <span className="text-destructive">-{totals.deletions}</span>
        </span>
        {analysis.model && (
          <span className="text-xs text-muted-foreground">· {analysis.model}</span>
        )}
      </div>

      {analysis.summary && (
        <section>
          <h2 className="text-sm font-semibold text-foreground">Summary</h2>
          <p className="mt-1.5 text-sm text-muted-foreground">{analysis.summary}</p>
        </section>
      )}

      {analysis.affected_components.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-foreground">Affected components</h2>
          <div className="mt-2 space-y-2">
            {analysis.affected_components.map((component) => (
              <div key={component.name} className="rounded-lg border border-border p-3">
                <p className="text-sm font-medium text-foreground">{component.name}</p>
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {component.file_paths.map((path) => (
                    <FileLink
                      key={path}
                      path={path}
                      repository={repository}
                      headSha={analysis.head_sha}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {analysis.potential_concerns.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-foreground">Potential concerns</h2>
          <ul className="mt-2 space-y-2">
            {analysis.potential_concerns.map((concern, i) => (
              <li key={i} className="rounded-lg border border-border p-3 text-sm">
                <p className="text-foreground">{concern.description}</p>
                {concern.file_path && (
                  <div className="mt-1.5">
                    <FileLink
                      path={concern.file_path}
                      repository={repository}
                      headSha={analysis.head_sha}
                      symbolName={concern.symbol_name}
                    />
                  </div>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {analysis.recommended_tests.length > 0 && (
        <section>
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
            <FlaskConicalIcon className="size-3.5" />
            Recommended tests
          </h2>
          <ul className="mt-2 space-y-2">
            {analysis.recommended_tests.map((test, i) => (
              <li key={i} className="rounded-lg border border-border p-3 text-sm">
                <p className="text-foreground">{test.description}</p>
                {test.existing_test_file ? (
                  <div className="mt-1.5 flex items-center gap-1.5">
                    <CheckCircle2Icon className="size-3.5 shrink-0 text-success" />
                    <FileLink
                      path={test.existing_test_file}
                      repository={repository}
                      headSha={analysis.head_sha}
                    />
                  </div>
                ) : (
                  <p className="mt-1 text-xs text-muted-foreground">No existing test covers this — net-new scenario.</p>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {analysis.files_analyzed.length > 0 && (
        <section>
          <h2 className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
            <FileCodeIcon className="size-3.5" />
            Files changed
          </h2>
          <div className="mt-2 overflow-hidden rounded-lg border border-border">
            <ul className="divide-y divide-border">
              {analysis.files_analyzed.map((file) => (
                <li
                  key={file.path}
                  className="flex items-center justify-between gap-3 px-3 py-2 text-xs"
                >
                  <div className="flex min-w-0 items-center gap-2">
                    <Badge variant={FILE_STATUS_VARIANT[file.status] ?? "outline"} className="shrink-0">
                      {file.status}
                    </Badge>
                    <a
                      href={buildBlobUrl(repository, file.path, { ref: analysis.head_sha })}
                      target="_blank"
                      rel="noreferrer"
                      className="truncate font-mono text-foreground hover:text-brand hover:underline"
                      title={file.path}
                    >
                      {file.path}
                    </a>
                    <ExternalLinkIcon className="size-3 shrink-0 text-muted-foreground" />
                  </div>
                  <span className="shrink-0 text-muted-foreground">
                    <span className="text-success">+{file.additions}</span>{" "}
                    <span className="text-destructive">-{file.deletions}</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}
    </div>
  );
}
