"use client";

import Link from "next/link";
import { CheckIcon, ChevronsUpDownIcon, PlusIcon } from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { StatusDot } from "@/components/shell/status-dot";
import { demoRepositories } from "@/lib/demo-data";

export function RepoSwitcher({
  workspaceSlug,
  activeRepoSlug,
}: {
  workspaceSlug: string;
  activeRepoSlug?: string;
}) {
  const active = demoRepositories.find((r) => r.slug === activeRepoSlug);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <button
            type="button"
            className="flex min-w-0 items-center gap-1.5 rounded-md px-2 py-1 text-sm font-medium hover:bg-muted"
          />
        }
      >
        <span className="min-w-0 truncate">{active ? active.name : "Select repository"}</span>
        <ChevronsUpDownIcon
          className="size-3.5 shrink-0 text-muted-foreground"
          aria-hidden="true"
        />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-72">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Repositories</DropdownMenuLabel>
          {demoRepositories.map((repo) => (
            <DropdownMenuItem
              key={repo.id}
              render={<Link href={`/${workspaceSlug}/${repo.slug}`} />}
              className="justify-between"
            >
              <span className="flex min-w-0 items-center gap-2">
                <StatusDot status={repo.status} />
                <span className="truncate">{repo.name}</span>
              </span>
              {repo.slug === activeRepoSlug && <CheckIcon className="size-4 text-brand" />}
            </DropdownMenuItem>
          ))}
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuItem render={<Link href={`/${workspaceSlug}`} />}>
          <PlusIcon className="size-4" />
          Connect repository
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
