"use client";

import { useRouter } from "next/navigation";
import { FolderGitIcon, SettingsIcon, LayoutGridIcon } from "lucide-react";

import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { useShell } from "@/components/shell/shell-context";
import { StatusDot } from "@/components/shell/status-dot";
import { demoRepositories, demoWorkspaces } from "@/lib/demo-data";

export function CommandPalette({ workspaceSlug }: { workspaceSlug: string }) {
  const { commandPaletteOpen, setCommandPaletteOpen } = useShell();
  const router = useRouter();

  function go(href: string) {
    setCommandPaletteOpen(false);
    router.push(href);
  }

  return (
    <CommandDialog open={commandPaletteOpen} onOpenChange={setCommandPaletteOpen}>
      <Command>
        <CommandInput placeholder="Search repositories, workspaces, settings…" />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup heading="Repositories">
            {demoRepositories.map((repo) => (
              <CommandItem
                key={repo.id}
                value={repo.name}
                onSelect={() => go(`/${workspaceSlug}/${repo.slug}`)}
              >
                <StatusDot status={repo.status} />
                {repo.name}
              </CommandItem>
            ))}
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading="Workspaces">
            {demoWorkspaces.map((workspace) => (
              <CommandItem
                key={workspace.id}
                value={workspace.name}
                onSelect={() => go(`/${workspace.slug}`)}
              >
                <LayoutGridIcon />
                {workspace.name}
              </CommandItem>
            ))}
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading="Navigation">
            <CommandItem value="Repositories" onSelect={() => go(`/${workspaceSlug}`)}>
              <FolderGitIcon />
              Go to repositories
            </CommandItem>
            <CommandItem value="Settings" onSelect={() => go(`/${workspaceSlug}/settings`)}>
              <SettingsIcon />
              Go to settings
            </CommandItem>
          </CommandGroup>
        </CommandList>
      </Command>
    </CommandDialog>
  );
}
