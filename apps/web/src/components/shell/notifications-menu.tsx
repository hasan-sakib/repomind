"use client";

import { BellIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

export function NotificationsMenu() {
  return (
    <Popover>
      <PopoverTrigger render={<Button variant="ghost" size="icon-sm" aria-label="Notifications" />}>
        <BellIcon className="size-4" />
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0">
        <div className="border-b border-border px-3 py-2 text-sm font-medium">Notifications</div>
        <p className="px-3 py-6 text-center text-sm text-muted-foreground">No notifications yet.</p>
      </PopoverContent>
    </Popover>
  );
}
