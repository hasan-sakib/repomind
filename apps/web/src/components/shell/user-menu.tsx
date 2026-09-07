"use client";

import { LogOutIcon, SettingsIcon } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { demoUser } from "@/lib/demo-data";

function initials(name: string) {
  return name
    .split(" ")
    .map((part) => part.charAt(0))
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function UserMenu() {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={
          <button
            type="button"
            aria-label="User menu"
            className="flex items-center gap-2 rounded-md p-1 hover:bg-sidebar-accent"
          />
        }
      >
        <Avatar className="size-6">
          <AvatarFallback className="text-[10px]">{initials(demoUser.name)}</AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuGroup>
          <DropdownMenuLabel className="flex flex-col gap-0.5 px-1.5 py-1">
            <span className="text-sm font-medium text-foreground">{demoUser.name}</span>
            <span className="truncate text-xs font-normal text-muted-foreground">
              {demoUser.email}
            </span>
          </DropdownMenuLabel>
        </DropdownMenuGroup>
        <DropdownMenuSeparator />
        <DropdownMenuGroup>
          <DropdownMenuItem disabled>
            <SettingsIcon className="size-4" />
            Account settings
          </DropdownMenuItem>
          <DropdownMenuItem disabled variant="destructive">
            <LogOutIcon className="size-4" />
            Log out
          </DropdownMenuItem>
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
