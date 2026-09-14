"use client";

import { usePathname } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";

import { cn } from "cn";

// Same 5 sections/colors as the sidebar's nav-items.tsx bar (chart-1..5, in
// the same order) — a clean, low-opacity wash across each section's own
// page(s) instead of a colored sidebar. Matches both the top-level nav page
// (e.g. /architecture) and its repo-scoped equivalent
// (/repositories/:id/architecture).
const SECTION_BG: Record<string, string> = {
  dashboard: "bg-chart-1/5",
  architecture: "bg-chart-2/5",
  onboarding: "bg-chart-3/5",
  analytics: "bg-chart-4/5",
  settings: "bg-chart-5/5",
};

function sectionBackground(pathname: string): string | undefined {
  const segments = pathname.split("/").filter(Boolean);
  const key =
    segments[0] === "repositories" && segments.length >= 3 ? segments[2] : segments[0];
  return key ? SECTION_BG[key] : undefined;
}

export function PageTransition({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <AnimatePresence mode="wait" initial={false}>
      <motion.div
        key={pathname}
        className={cn("flex h-full min-h-0 flex-col", sectionBackground(pathname))}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.12, ease: "easeOut" }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
