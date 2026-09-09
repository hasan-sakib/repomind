"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

import { applyRealtimeEvent } from "@/lib/realtime/apply-event";
import { type ConnectionStatus, RealtimeConnection } from "@/lib/realtime/connection";
import { useCurrentOrg } from "@/lib/current-org";
import type { NotificationLevel, RealtimeNotification } from "@/lib/types";

const MAX_NOTIFICATIONS = 30;

interface RealtimeContextValue {
  status: ConnectionStatus;
  notifications: RealtimeNotification[];
  unreadCount: number;
  markAllRead: () => void;
}

const RealtimeContext = createContext<RealtimeContextValue | null>(null);

/** One WebSocket for the whole app, scoped to the current organization —
 * mounted once in DashboardShellClient, inside CurrentOrgProvider. Reopens
 * on an organization switch and always tears the old connection down
 * first (the effect's cleanup runs before the next effect body), so
 * there's never more than one open connection at a time. */
export function RealtimeProvider({ children }: { children: React.ReactNode }) {
  const { currentOrg } = useCurrentOrg();
  const organizationId = currentOrg?.organization.id;
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [notifications, setNotifications] = useState<RealtimeNotification[]>([]);

  useEffect(() => {
    if (!organizationId) return;

    // Switching organizations starts a fresh notification list — the
    // old channel's events don't apply to the newly-selected org. This
    // only ever runs when `organizationId` actually changes (it's the
    // effect's own dependency), not on every render.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setNotifications([]);

    const connection = new RealtimeConnection(
      organizationId,
      (nextStatus) => setStatus(nextStatus),
      (event) => {
        if (event.category === "notification") {
          if (!event.title) return;
          const notification: RealtimeNotification = {
            id: event.id,
            title: event.title,
            level: (event.level ?? "info") as NotificationLevel,
            repositoryId: event.repository_id,
            at: event.at,
            read: false,
          };
          setNotifications((prev) => [notification, ...prev].slice(0, MAX_NOTIFICATIONS));
          return;
        }
        applyRealtimeEvent(queryClient, event);
      },
    );
    connection.start();

    return () => connection.stop();
  }, [organizationId, queryClient]);

  function markAllRead() {
    setNotifications((prev) => prev.map((n) => (n.read ? n : { ...n, read: true })));
  }

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <RealtimeContext.Provider value={{ status, notifications, unreadCount, markAllRead }}>
      {children}
    </RealtimeContext.Provider>
  );
}

export function useRealtime() {
  const context = useContext(RealtimeContext);
  if (!context) {
    throw new Error("useRealtime must be used within a RealtimeProvider");
  }
  return context;
}
