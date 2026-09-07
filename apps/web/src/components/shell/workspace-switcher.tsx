"use client";

import Link from "next/link";
import { CheckIcon, ChevronsUpDownIcon, PlusIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { demoWorkspaces } from "@/lib/demo-data";
import { cn } from "cn";

export function WorkspaceSwitcher({ activeSlug }: { activeSlug: string }) {
  const active = demoWorkspaces.find((w) => w.slug === activeSlug) ?? demoWorkspaces[0];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <button
            type="button"
            className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm font-medium text-sidebar-foreground hover:bg-sidebar-accent"
          />
        }
      >
        <span className="flex size-5 shrink-0 items-center justify-center rounded-[6px] bg-brand/15 text-[11px] font-semibold text-brand">
          {active.name.charAt(0).toUpperCase()}
        </span>
        <span className="min-w-0 flex-1 truncate">{active.name}</span>
        <ChevronsUpDownIcon
          className="size-3.5 shrink-0 text-muted-foreground"
          aria-hidden="true"
        />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-64">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Workspaces</DropdownMenuLabel>
          {demoWorkspaces.map((workspace) => (
            <DropdownMenuItem
              key={workspace.id}
              render={<Link href={`/${workspace.slug}`} />}
              className="justify-between"
            >
              <span className="flex items-center gap-2">
                <span
                  className={cn(
                    "flex size-5 shrink-0 items-center justify-center rounded-[6px] text-[11px] font-semibold",
                    workspace.slug === active.slug
                      ? "bg-brand/15 text-brand"
                      : "bg-muted text-muted-foreground",
                  )}
                >
                  {workspace.name.charAt(0).toUpperCase()}
                </span>
                {workspace.name}
                {workspace.plan === "team" && (
                  <Badge variant="outline" className="h-4 px-1.5 text-[10px]">
                    Team
                  </Badge>
                )}
              </span>
              {workspace.slug === active.slug && <CheckIcon className="size-4 text-brand" />}
            </DropdownMenuItem>
          ))}
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem disabled className="text-muted-foreground">
          <PlusIcon className="size-4" />
          Create workspace
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
