"use client";

import { BellIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { demoNotifications } from "@/lib/demo-data";
import { cn } from "cn";

function formatRelativeTime(iso: string) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const hours = Math.round(diffMs / (1000 * 60 * 60));
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}

export function NotificationsMenu() {
  const unreadCount = demoNotifications.filter((n) => !n.read).length;

  return (
    <Popover>
      <PopoverTrigger
        render={
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={`Notifications (${unreadCount} unread)`}
          />
        }
      >
        <span className="relative">
          <BellIcon className="size-4" />
          {unreadCount > 0 && (
            <span className="absolute -top-1 -right-1 flex size-2 rounded-full bg-brand" />
          )}
        </span>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 p-0">
        <div className="border-b border-border px-3 py-2 text-sm font-medium">Notifications</div>
        <ul className="max-h-80 overflow-y-auto">
          {demoNotifications.map((notification) => (
            <li
              key={notification.id}
              className={cn(
                "border-b border-border px-3 py-2.5 text-sm last:border-b-0",
                !notification.read && "bg-brand/5",
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <p className="font-medium text-foreground">{notification.title}</p>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {formatRelativeTime(notification.createdAt)}
                </span>
              </div>
              <p className="mt-0.5 text-xs text-muted-foreground">{notification.description}</p>
            </li>
          ))}
        </ul>
      </PopoverContent>
    </Popover>
  );
}
