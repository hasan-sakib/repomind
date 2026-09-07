"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { FolderGitIcon, SettingsIcon } from "lucide-react";

import { cn } from "cn";

export function getNavItems(workspaceSlug: string) {
  return [
    {
      label: "Repositories",
      href: `/${workspaceSlug}`,
      icon: FolderGitIcon,
      segment: null,
    },
    {
      label: "Settings",
      href: `/${workspaceSlug}/settings`,
      icon: SettingsIcon,
      segment: "settings",
    },
  ];
}

export function NavList({
  workspaceSlug,
  onNavigate,
}: {
  workspaceSlug: string;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const items = getNavItems(workspaceSlug);

  return (
    <nav aria-label="Primary" className="flex flex-col gap-0.5 px-2">
      {items.map((item) => {
        const isActive =
          item.href === pathname || (item.segment !== null && pathname.startsWith(`${item.href}/`));
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium transition-colors",
              isActive
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
            )}
          >
            <Icon className="size-4 shrink-0" aria-hidden="true" />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
