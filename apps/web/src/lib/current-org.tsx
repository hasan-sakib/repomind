"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";

import type { OrganizationMembership } from "@/lib/types";

const STORAGE_KEY = "repomind.currentOrgId";

interface CurrentOrgContextValue {
  organizations: OrganizationMembership[];
  currentOrg: OrganizationMembership | undefined;
  setCurrentOrgId: (id: string) => void;
}

const CurrentOrgContext = createContext<CurrentOrgContextValue | null>(null);

export function CurrentOrgProvider({
  organizations,
  children,
}: {
  organizations: OrganizationMembership[];
  children: React.ReactNode;
}) {
  const [currentOrgId, setCurrentOrgIdState] = useState<string | undefined>(
    organizations[0]?.organization.id,
  );

  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = localStorage.getItem(STORAGE_KEY);
    } catch {
      // Private browsing / storage disabled — fall back to the default.
    }
    if (stored && organizations.some((m) => m.organization.id === stored)) {
      // Reading localStorage is only possible client-side after mount, so
      // this genuinely has to run in an effect, not a lazy useState
      // initializer (which would throw during server rendering).
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setCurrentOrgIdState(stored);
    }
    // Only run once, on mount — subsequent changes go through setCurrentOrgId.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function setCurrentOrgId(id: string) {
    setCurrentOrgIdState(id);
    try {
      localStorage.setItem(STORAGE_KEY, id);
    } catch {
      // Ignore — the selection just won't persist across reloads.
    }
  }

  const currentOrg = useMemo(
    () => organizations.find((m) => m.organization.id === currentOrgId),
    [organizations, currentOrgId],
  );

  return (
    <CurrentOrgContext.Provider value={{ organizations, currentOrg, setCurrentOrgId }}>
      {children}
    </CurrentOrgContext.Provider>
  );
}

export function useCurrentOrg() {
  const context = useContext(CurrentOrgContext);
  if (!context) {
    throw new Error("useCurrentOrg must be used within a CurrentOrgProvider");
  }
  return context;
}
