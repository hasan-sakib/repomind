"use client";

import { use } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangleIcon,
  BookMarkedIcon,
  BookOpenIcon,
  BoxesIcon,
  DatabaseIcon,
  HelpCircleIcon,
  MapIcon,
  NetworkIcon,
  RefreshCwIcon,
  ShieldIcon,
  SparklesIcon,
  WrenchIcon,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/empty-state";
import { ErrorState } from "@/components/error-state";
import { FaqList } from "@/components/onboarding/faq-list";
import {
  ArchitectureContent,
  AuthFlowContent,
  DatabaseStructureList,
  DevSetupContent,
  ImportantModulesList,
  RecommendedReadingList,
  RepositoryIntro,
} from "@/components/onboarding/guide-content";
import { LearningPathPanel } from "@/components/onboarding/learning-path-panel";
import { OnboardingSection } from "@/components/onboarding/section";
import { ApiError } from "@/lib/api-client";
import {
  getOnboardingGuide,
  getOnboardingProgress,
  setOnboardingProgress,
  triggerOnboardingGuide,
} from "@/lib/api/onboarding";
import { getRepositoryOverview } from "@/lib/api/repositories";

const SECTIONS = [
  { key: "section:repository-intro", title: "Repository Introduction", icon: BookOpenIcon },
  { key: "section:architecture", title: "Architecture", icon: NetworkIcon },
  { key: "section:important-modules", title: "Important Modules", icon: BoxesIcon },
  { key: "section:auth-flow", title: "Authentication Flow", icon: ShieldIcon },
  { key: "section:database-structure", title: "Database Structure", icon: DatabaseIcon },
  { key: "section:dev-setup", title: "Development Setup", icon: WrenchIcon },
  { key: "section:recommended-reading", title: "Recommended Reading", icon: BookMarkedIcon },
  { key: "section:faq", title: "Frequently Asked Questions", icon: HelpCircleIcon },
] as const;

const ACTIVE_STATUSES = new Set(["queued", "running"]);

export default function OnboardingPage({
  params,
}: {
  params: Promise<{ repositoryId: string }>;
}) {
  const { repositoryId } = use(params);
  const queryClient = useQueryClient();

  const overviewQuery = useQuery({
    queryKey: ["repository-overview", repositoryId],
    queryFn: () => getRepositoryOverview(repositoryId),
  });

  const guideQuery = useQuery({
    queryKey: ["onboarding-guide", repositoryId],
    queryFn: () => getOnboardingGuide(repositoryId),
    retry: (failureCount, error) =>
      !(error instanceof ApiError && error.code === "onboarding_guide_not_found") &&
      failureCount < 2,
    refetchInterval: (query) =>
      query.state.data && ACTIVE_STATUSES.has(query.state.data.status) ? 2000 : false,
  });

  const progressQuery = useQuery({
    queryKey: ["onboarding-progress", repositoryId],
    queryFn: () => getOnboardingProgress(repositoryId),
  });

  const triggerMutation = useMutation({
    mutationFn: (force: boolean) => triggerOnboardingGuide(repositoryId, { force }),
    onSuccess: (guide) => {
      queryClient.setQueryData(["onboarding-guide", repositoryId], guide);
      queryClient.invalidateQueries({ queryKey: ["onboarding-guide", repositoryId] });
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ itemKey, completed }: { itemKey: string; completed: boolean }) =>
      setOnboardingProgress(repositoryId, itemKey, completed),
    onMutate: async ({ itemKey, completed }) => {
      await queryClient.cancelQueries({ queryKey: ["onboarding-progress", repositoryId] });
      const previous =
        queryClient.getQueryData<string[]>(["onboarding-progress", repositoryId]) ?? [];
      const next = completed
        ? [...new Set([...previous, itemKey])]
        : previous.filter((k) => k !== itemKey);
      queryClient.setQueryData(["onboarding-progress", repositoryId], next);
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context) {
        queryClient.setQueryData(["onboarding-progress", repositoryId], context.previous);
      }
    },
  });

  function toggle(itemKey: string, completed: boolean) {
    toggleMutation.mutate({ itemKey, completed });
  }

  if (overviewQuery.isPending || progressQuery.isPending) {
    return (
      <div className="mx-auto max-w-5xl space-y-4 px-4 py-6 sm:px-6">
        <Skeleton className="h-7 w-64" />
        <Skeleton className="h-40 w-full" />
      </div>
    );
  }

  if (overviewQuery.isError) {
    return (
      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
        <ErrorState
          title="Couldn't load this repository"
          description="It may have been disconnected, or you may no longer have access."
          onRetry={() => overviewQuery.refetch()}
        />
      </div>
    );
  }

  const { repository } = overviewQuery.data;
  const guide = guideQuery.data;
  const completed = new Set(progressQuery.data ?? []);
  const isActive = guide != null && ACTIVE_STATUSES.has(guide.status);

  const notOnboarded =
    guideQuery.isError &&
    guideQuery.error instanceof ApiError &&
    guideQuery.error.code === "onboarding_guide_not_found";
  const notIndexed =
    triggerMutation.isError &&
    triggerMutation.error instanceof ApiError &&
    triggerMutation.error.code === "repository_not_indexed";

  const totalItems = guide ? 8 + guide.learning_path.length : 0;
  const completedCount = guide
    ? SECTIONS.filter((s) => completed.has(s.key)).length +
      guide.learning_path.filter((s) => completed.has(`step:${s.step}`)).length
    : 0;
  const percent = totalItems > 0 ? (completedCount / totalItems) * 100 : 0;

  return (
    <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">
            {repository.full_name} onboarding
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Everything a new developer needs to get productive in this repository.
          </p>
        </div>
        <Button
          size="sm"
          variant={guide ? "outline" : "default"}
          disabled={isActive || triggerMutation.isPending}
          onClick={() => triggerMutation.mutate(!!guide)}
        >
          <SparklesIcon className="size-3.5" />
          {isActive ? "Generating…" : guide ? "Regenerate" : "Generate guide"}
        </Button>
      </div>

      {guide?.status === "succeeded" && (
        <div className="mt-4 flex items-center gap-3">
          <Progress value={percent} className="flex-1" />
          <span className="shrink-0 text-xs text-muted-foreground">
            {completedCount}/{totalItems} complete
          </span>
        </div>
      )}

      {notIndexed && (
        <div className="mt-4 rounded-lg border border-warning/30 bg-warning/5 px-3 py-2 text-sm text-warning-foreground">
          Index this repository before generating an onboarding guide.{" "}
          <Link href={`/repositories/${repositoryId}/indexing`} className="underline">
            Go to indexing
          </Link>
          .
        </div>
      )}

      {notOnboarded && !notIndexed && (
        <div className="mt-6">
          <EmptyState
            icon={SparklesIcon}
            title="No onboarding guide yet"
            description="Generate one to get a repository overview, architecture summary, learning path, and more — grounded in this repository's actual code."
            action={
              <Button onClick={() => triggerMutation.mutate(false)} disabled={triggerMutation.isPending}>
                <SparklesIcon className="size-3.5" />
                Generate guide
              </Button>
            }
          />
        </div>
      )}

      {guideQuery.isError && !notOnboarded && (
        <div className="mt-6">
          <ErrorState description="Couldn't load the onboarding guide." onRetry={() => guideQuery.refetch()} />
        </div>
      )}

      {guide?.status === "queued" && (
        <div className="mt-6 flex flex-col items-center justify-center gap-2 rounded-lg border border-border px-6 py-16 text-center">
          <SparklesIcon className="size-5 animate-pulse text-brand" />
          <p className="text-sm text-muted-foreground">Waiting to start…</p>
        </div>
      )}

      {guide?.status === "running" && (
        <div className="mt-6 flex flex-col items-center justify-center gap-2 rounded-lg border border-border px-6 py-16 text-center">
          <RefreshCwIcon className="size-5 animate-spin text-brand" />
          <p className="text-sm text-muted-foreground">
            Analyzing modules, dependencies, and structure…
          </p>
        </div>
      )}

      {guide?.status === "failed" && (
        <div className="mt-6 flex flex-col items-center justify-center gap-3 rounded-lg border border-destructive/30 bg-destructive/5 px-6 py-12 text-center">
          <AlertTriangleIcon className="size-5 text-destructive" />
          <div className="space-y-1">
            <p className="text-sm font-medium text-foreground">Generation failed</p>
            <p className="max-w-sm text-sm text-muted-foreground">
              {guide.error ?? "An unexpected error occurred."}
            </p>
          </div>
          <Button
            size="sm"
            variant="outline"
            onClick={() => triggerMutation.mutate(true)}
            disabled={triggerMutation.isPending}
          >
            <RefreshCwIcon className="size-3.5" />
            Try again
          </Button>
        </div>
      )}

      {guide?.status === "succeeded" && (
        <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-[1fr_20rem]">
          <div className="min-w-0 space-y-4">
            <OnboardingSection
              itemKey="section:repository-intro"
              icon={BookOpenIcon}
              title="Repository Introduction"
              completed={completed.has("section:repository-intro")}
              onToggle={(c) => toggle("section:repository-intro", c)}
            >
              <RepositoryIntro repository={repository} />
            </OnboardingSection>

            <OnboardingSection
              itemKey="section:architecture"
              icon={NetworkIcon}
              title="Architecture"
              completed={completed.has("section:architecture")}
              onToggle={(c) => toggle("section:architecture", c)}
            >
              <ArchitectureContent
                architectureOverview={guide.architecture_overview}
                commonWorkflows={guide.common_workflows}
              />
            </OnboardingSection>

            <OnboardingSection
              itemKey="section:important-modules"
              icon={BoxesIcon}
              title="Important Modules"
              completed={completed.has("section:important-modules")}
              onToggle={(c) => toggle("section:important-modules", c)}
            >
              <ImportantModulesList modules={guide.important_modules} />
            </OnboardingSection>

            <OnboardingSection
              itemKey="section:auth-flow"
              icon={ShieldIcon}
              title="Authentication Flow"
              completed={completed.has("section:auth-flow")}
              onToggle={(c) => toggle("section:auth-flow", c)}
            >
              <AuthFlowContent authenticationFlow={guide.authentication_flow} />
            </OnboardingSection>

            <OnboardingSection
              itemKey="section:database-structure"
              icon={DatabaseIcon}
              title="Database Structure"
              completed={completed.has("section:database-structure")}
              onToggle={(c) => toggle("section:database-structure", c)}
            >
              <DatabaseStructureList
                entries={guide.database_structure}
                repository={repository}
                gitRef={guide.commit_sha}
              />
            </OnboardingSection>

            <OnboardingSection
              itemKey="section:dev-setup"
              icon={WrenchIcon}
              title="Development Setup"
              completed={completed.has("section:dev-setup")}
              onToggle={(c) => toggle("section:dev-setup", c)}
            >
              <DevSetupContent steps={guide.dev_setup_steps} dependencies={guide.key_dependencies} />
            </OnboardingSection>

            <OnboardingSection
              itemKey="section:recommended-reading"
              icon={BookMarkedIcon}
              title="Recommended Reading"
              completed={completed.has("section:recommended-reading")}
              onToggle={(c) => toggle("section:recommended-reading", c)}
            >
              <RecommendedReadingList
                files={guide.recommended_files}
                repository={repository}
                gitRef={guide.commit_sha}
              />
            </OnboardingSection>

            <OnboardingSection
              itemKey="section:faq"
              icon={HelpCircleIcon}
              title="Frequently Asked Questions"
              completed={completed.has("section:faq")}
              onToggle={(c) => toggle("section:faq", c)}
            >
              <FaqList entries={guide.faq} repository={repository} gitRef={guide.commit_sha} />
            </OnboardingSection>
          </div>

          <aside className="lg:sticky lg:top-4 lg:h-fit">
            <div className="rounded-lg border border-border p-3">
              <h2 className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
                <MapIcon className="size-4" />
                Start Here
              </h2>
              <div className="mt-3">
                <LearningPathPanel
                  steps={guide.learning_path}
                  repository={repository}
                  gitRef={guide.commit_sha}
                  completedSteps={
                    new Set(
                      guide.learning_path
                        .filter((s) => completed.has(`step:${s.step}`))
                        .map((s) => s.step),
                    )
                  }
                  onToggle={(step, c) => toggle(`step:${step}`, c)}
                />
              </div>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
