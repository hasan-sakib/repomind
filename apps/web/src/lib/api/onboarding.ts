import { apiFetch } from "@/lib/api-client";
import type { OnboardingGuide } from "@/lib/types";

export function getOnboardingGuide(repositoryId: string): Promise<OnboardingGuide> {
  return apiFetch(`/api/v1/repositories/${repositoryId}/onboarding`);
}

export function triggerOnboardingGuide(
  repositoryId: string,
  options: { force?: boolean } = {},
): Promise<OnboardingGuide> {
  const query = options.force ? "?force=true" : "";
  return apiFetch(`/api/v1/repositories/${repositoryId}/onboarding${query}`, { method: "POST" });
}

export function getOnboardingProgress(repositoryId: string): Promise<string[]> {
  return apiFetch(`/api/v1/repositories/${repositoryId}/onboarding/progress`);
}

export function setOnboardingProgress(
  repositoryId: string,
  itemKey: string,
  completed: boolean,
): Promise<void> {
  return apiFetch(
    `/api/v1/repositories/${repositoryId}/onboarding/progress/${encodeURIComponent(itemKey)}`,
    { method: "PUT", body: JSON.stringify({ completed }) },
  );
}
