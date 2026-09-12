"use client";

import { useState } from "react";
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
import { CreateOrgDialog } from "@/components/shell/create-org-dialog";
import { useCurrentOrg } from "@/lib/current-org";
import { cn } from "cn";

export function OrgSwitcher() {
  const { organizations, currentOrg, setCurrentOrgId } = useCurrentOrg();
  const [createOpen, setCreateOpen] = useState(false);

  if (!currentOrg) return null;

  return (
    <>
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
            {currentOrg.organization.name.charAt(0).toUpperCase()}
          </span>
          <span className="min-w-0 flex-1 truncate">{currentOrg.organization.name}</span>
          <ChevronsUpDownIcon
            className="size-3.5 shrink-0 text-muted-foreground"
            aria-hidden="true"
          />
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-64">
          <DropdownMenuGroup>
            <DropdownMenuLabel>Organizations</DropdownMenuLabel>
            {organizations.map((membership) => (
              <DropdownMenuItem
                key={membership.organization.id}
                onClick={() => setCurrentOrgId(membership.organization.id)}
                className="justify-between"
              >
                <span className="flex items-center gap-2">
                  <span
                    className={cn(
                      "flex size-5 shrink-0 items-center justify-center rounded-[6px] text-[11px] font-semibold",
                      membership.organization.id === currentOrg.organization.id
                        ? "bg-brand/15 text-brand"
                        : "bg-muted text-muted-foreground",
                    )}
                  >
                    {membership.organization.name.charAt(0).toUpperCase()}
                  </span>
                  {membership.organization.name}
                </span>
                {membership.organization.id === currentOrg.organization.id && (
                  <CheckIcon className="size-4 text-brand" />
                )}
              </DropdownMenuItem>
            ))}
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setCreateOpen(true)}>
            <PlusIcon className="size-4" />
            Create organization
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <CreateOrgDialog open={createOpen} onOpenChange={setCreateOpen} />
    </>
  );
}
