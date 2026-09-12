import { CheckCircle2Icon, CircleIcon, ExternalLinkIcon } from "lucide-react";

import { buildBlobUrl } from "@/lib/github-url";
import type { LearningPathStep, Repository } from "@/lib/types";
import { cn } from "cn";

export function LearningPathPanel({
  steps,
  repository,
  gitRef,
  completedSteps,
  onToggle,
}: {
  steps: LearningPathStep[];
  repository: Repository;
  gitRef: string;
  completedSteps: Set<number>;
  onToggle: (step: number, completed: boolean) => void;
}) {
  if (steps.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">
        Not enough was detected in this repository to build a learning path yet.
      </p>
    );
  }

  return (
    <ol className="space-y-1">
      {steps.map((step) => {
        const isCompleted = completedSteps.has(step.step);
        return (
          <li
            key={step.step}
            className={cn(
              "flex items-start gap-2 rounded-lg border p-2.5 text-sm",
              isCompleted ? "border-success/30 bg-success/5" : "border-border",
            )}
          >
            <button
              type="button"
              onClick={() => onToggle(step.step, !isCompleted)}
              className="mt-0.5 shrink-0 text-muted-foreground hover:text-foreground"
              aria-label={isCompleted ? "Mark as unread" : "Mark as read"}
            >
              {isCompleted ? (
                <CheckCircle2Icon className="size-4 text-success" />
              ) : (
                <CircleIcon className="size-4" />
              )}
            </button>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-medium text-muted-foreground">{step.step}.</span>
                {step.path ? (
                  <a
                    href={buildBlobUrl(repository, step.path, { ref: gitRef })}
                    target="_blank"
                    rel="noreferrer"
                    className="truncate font-medium text-foreground hover:text-brand hover:underline"
                  >
                    {step.label}
                  </a>
                ) : (
                  <span className="truncate font-medium text-foreground">{step.label}</span>
                )}
                {step.path && (
                  <ExternalLinkIcon className="size-3 shrink-0 text-muted-foreground" />
                )}
              </div>
              {step.path && (
                <p className="truncate font-mono text-xs text-muted-foreground">{step.path}</p>
              )}
              <p className="mt-0.5 text-xs text-muted-foreground">{step.reason}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
