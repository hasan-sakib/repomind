import type { ReactElement, ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";

import { CurrentOrgProvider } from "@/lib/current-org";
import type { OrganizationMembership } from "@/lib/types";
import { makeOrganizationMembership } from "./factories";

/** A fresh QueryClient per render — retries/caching would otherwise make
 * tests slow and order-dependent (a failed request retrying in the
 * background after the test already asserted on it). */
export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

export function renderWithProviders(
  ui: ReactElement,
  {
    organizations = [makeOrganizationMembership()],
    queryClient = createTestQueryClient(),
    ...options
  }: {
    organizations?: OrganizationMembership[];
    queryClient?: QueryClient;
  } & Omit<RenderOptions, "wrapper"> = {},
) {
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <CurrentOrgProvider organizations={organizations}>{children}</CurrentOrgProvider>
      </QueryClientProvider>
    );
  }

  return render(ui, { wrapper: Wrapper, ...options });
}

export * from "@testing-library/react";
