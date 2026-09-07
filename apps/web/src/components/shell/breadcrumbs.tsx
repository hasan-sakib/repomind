"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRightIcon } from "lucide-react";
import { Fragment } from "react";

import { demoRepositories } from "@/lib/demo-data";

const SEGMENT_LABELS: Record<string, string> = {
  settings: "Settings",
};

export function Breadcrumbs({ workspaceSlug }: { workspaceSlug: string }) {
  const pathname = usePathname();
  const rest = pathname.replace(`/${workspaceSlug}`, "").split("/").filter(Boolean);

  const crumbs = rest.map((segment, index) => {
    const href = `/${workspaceSlug}/${rest.slice(0, index + 1).join("/")}`;
    const repo = demoRepositories.find((r) => r.slug === segment);
    const label = repo?.name ?? SEGMENT_LABELS[segment] ?? segment;
    return { href, label };
  });

  return (
    <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-1 text-sm">
      <Link
        href={`/${workspaceSlug}`}
        className="shrink-0 font-medium text-foreground hover:text-brand"
      >
        Repositories
      </Link>
      {crumbs.map((crumb) => (
        <Fragment key={crumb.href}>
          <ChevronRightIcon
            className="size-3.5 shrink-0 text-muted-foreground"
            aria-hidden="true"
          />
          <Link href={crumb.href} className="truncate text-muted-foreground hover:text-foreground">
            {crumb.label}
          </Link>
        </Fragment>
      ))}
    </nav>
  );
}
