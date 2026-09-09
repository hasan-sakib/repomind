"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronRightIcon } from "lucide-react";
import { Fragment } from "react";

const SEGMENT_LABELS: Record<string, string> = {
  dashboard: "Dashboard",
  settings: "Settings",
  members: "Members",
  repositories: "Repositories",
  connect: "Connect",
  indexing: "Indexing",
  chat: "Chat",
  architecture: "Architecture",
};

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

// What a UUID segment means depends on what precedes it — a repository id
// right after "repositories" is that repository's overview, but a UUID
// after "chat" is a specific conversation, not another "Overview" page.
const UUID_LABEL_BY_PARENT: Record<string, string> = {
  repositories: "Overview",
  chat: "Conversation",
};

// The "repositories" URL segment has no page of its own — the list lives
// at /dashboard — so its breadcrumb must point there instead of forming
// the literal (non-existent) /repositories URL.
const SEGMENT_HREF_OVERRIDES: Record<string, string> = {
  repositories: "/dashboard",
};

export function Breadcrumbs() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);

  const crumbs = segments.map((segment, index) => {
    const href = SEGMENT_HREF_OVERRIDES[segment] ?? `/${segments.slice(0, index + 1).join("/")}`;
    const parent = segments[index - 1];
    const label = UUID_PATTERN.test(segment)
      ? (UUID_LABEL_BY_PARENT[parent] ?? "Overview")
      : (SEGMENT_LABELS[segment] ?? segment);
    return { href, label };
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
