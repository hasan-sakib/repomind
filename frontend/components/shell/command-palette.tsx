"use client";

import { useRouter } from "next/navigation";
import {
  BarChart3Icon,
  BookOpenIcon,
  LayoutDashboardIcon,
  LayoutGridIcon,
  NetworkIcon,
  SettingsIcon,
  UsersIcon,
} from "lucide-react";

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
import { useCurrentOrg } from "@/lib/current-org";

export function CommandPalette() {
  const { commandPaletteOpen, setCommandPaletteOpen } = useShell();
  const { organizations, setCurrentOrgId } = useCurrentOrg();
  const router = useRouter();

  function go(href: string) {
    setCommandPaletteOpen(false);
    router.push(href);
  }

  return (
    <CommandDialog open={commandPaletteOpen} onOpenChange={setCommandPaletteOpen}>
      <Command>
        <CommandInput placeholder="Search organizations, settings…" />
        <CommandList>
          <CommandEmpty>No results found.</CommandEmpty>
          <CommandGroup heading="Navigation">
            <CommandItem value="Dashboard" onSelect={() => go("/dashboard")}>
              <LayoutDashboardIcon />
              Go to dashboard
            </CommandItem>
            <CommandItem value="Architecture" onSelect={() => go("/architecture")}>
              <NetworkIcon />
              Go to architecture
            </CommandItem>
            <CommandItem value="Onboarding" onSelect={() => go("/onboarding")}>
              <BookOpenIcon />
              Go to onboarding
            </CommandItem>
            <CommandItem value="Analytics" onSelect={() => go("/analytics")}>
              <BarChart3Icon />
              Go to analytics
            </CommandItem>
            <CommandItem value="Settings" onSelect={() => go("/settings")}>
              <SettingsIcon />
              Go to settings
            </CommandItem>
            <CommandItem value="Members" onSelect={() => go("/settings/members")}>
              <UsersIcon />
              Go to members
            </CommandItem>
          </CommandGroup>
          <CommandSeparator />
          <CommandGroup heading="Organizations">
            {organizations.map((membership) => (
              <CommandItem
                key={membership.organization.id}
                value={membership.organization.name}
                onSelect={() => {
                  setCurrentOrgId(membership.organization.id);
                  setCommandPaletteOpen(false);
                }}
              >
                <LayoutGridIcon />
                {membership.organization.name}
              </CommandItem>
            ))}
          </CommandGroup>
        </CommandList>
      </Command>
    </CommandDialog>
  );
}
