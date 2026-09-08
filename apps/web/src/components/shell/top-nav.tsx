"use client";

import { MenuIcon, SearchIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Breadcrumbs } from "@/components/shell/breadcrumbs";
import { NotificationsMenu } from "@/components/shell/notifications-menu";
import { useShell } from "@/components/shell/shell-context";
import { UserMenu } from "@/components/shell/user-menu";

export function TopNav() {
  const { setMobileNavOpen, setCommandPaletteOpen } = useShell();

  return (
    <header className="flex h-12 shrink-0 items-center gap-2 border-b border-border px-3">
      <Button
        variant="ghost"
        size="icon-sm"
        className="lg:hidden"
        aria-label="Open navigation"
        onClick={() => setMobileNavOpen(true)}
      >
        <MenuIcon className="size-4" />
      </Button>
      <div className="min-w-0 flex-1">
        <Breadcrumbs />
      </div>
      <button
        type="button"
        onClick={() => setCommandPaletteOpen(true)}
        className="hidden items-center gap-2 rounded-md border border-input bg-background px-2.5 py-1 text-xs text-muted-foreground hover:bg-muted sm:flex"
      >
        <SearchIcon className="size-3.5" />
        Search
        <kbd className="ml-2 rounded border border-border bg-muted px-1 font-mono text-[10px]">
          ⌘K
        </kbd>
      </button>
      <Button
        variant="ghost"
        size="icon-sm"
        className="sm:hidden"
        aria-label="Search"
        onClick={() => setCommandPaletteOpen(true)}
      >
        <SearchIcon className="size-4" />
      </Button>
      <NotificationsMenu />
      <UserMenu />
    </header>
  );
}
