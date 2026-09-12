import { ExternalLinkIcon } from "lucide-react";

import { KIND_ICON } from "@/components/architecture/node-kind-icon";
import { FileChip } from "@/components/file-chip";
import { Badge } from "@/components/ui/badge";
import { buildBlobUrl } from "@/lib/github-url";
import {
  NODE_KIND_LABELS,
  type DatabaseStructureEntry,
  type ImportantModule,
  type NodeKind,
  type OnboardingDependency,
  type RecommendedFile,
  type Repository,
  type SetupStep,
} from "@/lib/types";

export function RepositoryIntro({ repository }: { repository: Repository }) {
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-base font-medium text-foreground">{repository.full_name}</h3>
        <a
          href={repository.html_url}
          target="_blank"
          rel="noreferrer"
          className="text-muted-foreground hover:text-foreground"
          aria-label="Open on GitHub"
        >
          <ExternalLinkIcon className="size-3.5" />
        </a>
      </div>
      {repository.description && (
        <p className="text-sm text-muted-foreground">{repository.description}</p>
      )}
      <div className="flex flex-wrap gap-1.5 text-xs text-muted-foreground">
        {repository.language && <Badge variant="outline">{repository.language}</Badge>}
        <Badge variant="outline">★ {repository.stargazers_count}</Badge>
        <Badge variant="outline">⑂ {repository.forks_count}</Badge>
        <Badge variant="outline">default branch: {repository.default_branch}</Badge>
      </div>
    </div>
  );
}

export function ArchitectureContent({
  architectureOverview,
  commonWorkflows,
}: {
  architectureOverview: string | null;
  commonWorkflows: string | null;
}) {
  if (!architectureOverview && !commonWorkflows) {
    return (
      <p className="text-sm text-muted-foreground">
        Not enough indexed structure was found to describe this repository&apos;s architecture yet.
      </p>
    );
  }
  return (
    <div className="space-y-3">
      {architectureOverview && (
        <p className="text-sm text-muted-foreground">{architectureOverview}</p>
      )}
      {commonWorkflows && (
        <div>
          <p className="text-xs font-medium text-foreground">Common workflows</p>
          <p className="mt-1 text-sm text-muted-foreground">{commonWorkflows}</p>
        </div>
      )}
    </div>
  );
}

export function ImportantModulesList({ modules }: { modules: ImportantModule[] }) {
  if (modules.length === 0) {
    return <p className="text-sm text-muted-foreground">No modules were detected.</p>;
  }
  return (
    <ul className="space-y-2">
      {modules.map((module) => {
        const Icon = KIND_ICON[module.kind as NodeKind];
        return (
          <li
            key={module.path}
            className="flex items-center justify-between gap-3 rounded-lg border border-border p-2.5 text-sm"
          >
            <div className="flex min-w-0 items-center gap-2">
              <Icon className="size-4 shrink-0 text-muted-foreground" />
              <span className="truncate font-mono text-xs text-foreground">
                {module.path || "(root)"}
              </span>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <Badge variant="outline" className="text-[10px]">
                {NODE_KIND_LABELS[module.kind as NodeKind] ?? module.kind}
              </Badge>
              <span className="text-xs text-muted-foreground">
                {module.file_count} {module.file_count === 1 ? "file" : "files"}
              </span>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export function AuthFlowContent({ authenticationFlow }: { authenticationFlow: string | null }) {
  if (!authenticationFlow) {
    return (
      <p className="text-sm text-muted-foreground">
        No authentication-related files were detected in this repository.
      </p>
    );
  }
  return <p className="text-sm text-muted-foreground">{authenticationFlow}</p>;
}

export function DatabaseStructureList({
  entries,
  repository,
  gitRef,
}: {
  entries: DatabaseStructureEntry[];
  repository: Repository;
  gitRef: string;
}) {
  if (entries.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No model or data-access classes were detected in this repository.
      </p>
    );
  }
  return (
    <ul className="space-y-1.5">
      {entries.map((entry) => (
        <li
          key={`${entry.path}:${entry.class_name}`}
          className="flex flex-wrap items-center gap-2 text-sm"
        >
          <span className="font-medium text-foreground">{entry.class_name}</span>
          <span className="text-xs text-muted-foreground">{entry.symbol_type}</span>
          <FileChip path={entry.path} repository={repository} gitRef={gitRef} />
        </li>
      ))}
    </ul>
  );
}

const ECOSYSTEM_LABELS: Record<string, string> = { npm: "npm", python: "Python", go: "Go" };

export function DevSetupContent({
  steps,
  dependencies,
}: {
  steps: SetupStep[];
  dependencies: OnboardingDependency[];
}) {
  const byEcosystem = dependencies.reduce<Record<string, OnboardingDependency[]>>((acc, dep) => {
    (acc[dep.ecosystem] ??= []).push(dep);
    return acc;
  }, {});

  return (
    <div className="space-y-4">
      <ol className="space-y-1.5">
        {steps.map((step) => (
          <li key={step.order} className="rounded-lg border border-border p-2.5 text-sm">
            <div className="flex items-baseline gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">{step.order}.</span>
              <span className="text-foreground">{step.description}</span>
            </div>
            {step.command && (
              <code className="mt-1 block rounded bg-muted px-2 py-1 font-mono text-xs text-foreground">
                {step.command}
              </code>
            )}
          </li>
        ))}
      </ol>
      {dependencies.length > 0 && (
        <div>
          <p className="text-xs font-medium text-foreground">Key dependencies</p>
          <div className="mt-1.5 space-y-2">
            {Object.entries(byEcosystem).map(([ecosystem, deps]) => (
              <div key={ecosystem}>
                <p className="text-[10px] font-medium tracking-wide text-muted-foreground uppercase">
                  {ECOSYSTEM_LABELS[ecosystem] ?? ecosystem}
                </p>
                <div className="mt-1 flex flex-wrap gap-1.5">
                  {deps.slice(0, 20).map((dep) => (
                    <Badge key={dep.name} variant="outline" className="font-mono text-[10px]">
                      {dep.name}
                      {dep.version && <span className="text-muted-foreground"> {dep.version}</span>}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export function RecommendedReadingList({
  files,
  repository,
  gitRef,
}: {
  files: RecommendedFile[];
  repository: Repository;
  gitRef: string;
}) {
  if (files.length === 0) {
    return <p className="text-sm text-muted-foreground">No files stood out as central yet.</p>;
  }
  return (
    <ul className="space-y-1.5">
      {files.map((file) => {
        const Icon = KIND_ICON[file.kind as NodeKind];
        return (
          <li key={file.path} className="flex items-center justify-between gap-3 text-sm">
            <div className="flex min-w-0 items-center gap-2">
              <Icon className="size-3.5 shrink-0 text-muted-foreground" />
              <a
                href={buildBlobUrl(repository, file.path, { ref: gitRef })}
                target="_blank"
                rel="noreferrer"
                className="truncate font-mono text-xs text-foreground hover:text-brand hover:underline"
              >
                {file.path}
              </a>
            </div>
            <span className="shrink-0 text-xs text-muted-foreground">
              {file.dependents_count} {file.dependents_count === 1 ? "dependent" : "dependents"}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
