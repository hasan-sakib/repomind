"use client";

import Link from "next/link";
import { BellIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { formatRelativeTime } from "@/lib/format-time";
import { useRealtime } from "@/lib/realtime-context";
import { cn } from "cn";
import type { NotificationLevel } from "@/lib/types";

const LEVEL_DOT: Record<NotificationLevel, string> = {
  info: "bg-muted-foreground",
  success: "bg-success",
  error: "bg-destructive",
};

export function NotificationsMenu() {
  const { notifications, unreadCount, markAllRead } = useRealtime();

  return (
    <Popover onOpenChange={(open) => open && markAllRead()}>
      <PopoverTrigger
        render={<Button variant="ghost" size="icon-sm" aria-label="Notifications" />}
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
        {notifications.length === 0 ? (
          <p className="px-3 py-6 text-center text-sm text-muted-foreground">
            No notifications yet.
          </p>
        ) : (
          <ul className="max-h-80 overflow-y-auto">
            {notifications.map((notification) => (
              <li key={notification.id} className="border-b border-border last:border-0">
                <NotificationRow notification={notification} />
              </li>
            ))}
          </ul>
        )}
      </PopoverContent>
    </Popover>
  );
}

function NotificationRow({
  notification,
}: {
  notification: {
    id: string;
    title: string;
    level: NotificationLevel;
    repositoryId: string | null;
    at: string;
    read: boolean;
  };
}) {
  const content = (
    <div className="flex items-start gap-2 px-3 py-2 text-sm hover:bg-muted">
      <span
        className={cn("mt-1.5 size-1.5 shrink-0 rounded-full", LEVEL_DOT[notification.level])}
        aria-hidden="true"
      />
      <div className="min-w-0 flex-1">
        <p className="text-foreground">{notification.title}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {formatRelativeTime(notification.at)}
        </p>
      </div>
    </div>
  );

  if (!notification.repositoryId) {
    return content;
  }
  return <Link href={`/repositories/${notification.repositoryId}`}>{content}</Link>;
}
