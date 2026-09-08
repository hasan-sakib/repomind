"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRightIcon } from "lucide-react";
import { Fragment } from "react";

const SEGMENT_LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  settings: "Settings",
  members: "Members",
};

export function Breadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  const crumbs = segments.map((segment, index) => {
    const href = `/${segments.slice(0, index + 1).join("/")}`;
    return { href, label: SEGMENT_LABELS[segment] ?? segment };
  });

  return (
    <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-1 text-sm">
      {crumbs.map((crumb, index) => (
        <Fragment key={crumb.href}>
          {index > 0 && (
            <ChevronRightIcon
              className="size-3.5 shrink-0 text-muted-foreground"
              aria-hidden="true"
            />
          )}
          <Link
            href={crumb.href}
            className={
              index === crumbs.length - 1
                ? "truncate font-medium text-foreground"
                : "truncate text-muted-foreground hover:text-foreground"
            }
          >
            {crumb.label}
          </Link>
        </Fragment>
      ))}
    </nav>
  );
}
