"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import {
  BarChart3Icon,
  BookOpenIcon,
  LayoutDashboardIcon,
  NetworkIcon,
  SettingsIcon,
} from "lucide-react";

import { cn } from "cn";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboardIcon, barColor: "bg-chart-1" },
  { label: "Architecture", href: "/architecture", icon: NetworkIcon, barColor: "bg-chart-2" },
  { label: "Onboarding", href: "/onboarding", icon: BookOpenIcon, barColor: "bg-chart-3" },
  { label: "Analytics", href: "/analytics", icon: BarChart3Icon, barColor: "bg-chart-4" },
  { label: "Settings", href: "/settings", icon: SettingsIcon, barColor: "bg-chart-5" },
];

export function NavList({
  onNavigate,
  layoutGroupId = "sidebar",
}: {
  onNavigate?: () => void;
  /** Distinguishes the active-pill layout animation between the desktop
   * sidebar and the mobile sheet's copy of this list, so framer-motion
   * never sees two elements sharing one layoutId at once. */
  layoutGroupId?: string;
}) {
  const pathname = usePathname();

  return (
    <nav aria-label="Primary" className="flex flex-col gap-0.5 px-2">
      {NAV_ITEMS.map((item) => {
        const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            aria-current={isActive ? "page" : undefined}
            className={cn(
              "relative flex items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium transition-colors",
              isActive
                ? "text-sidebar-accent-foreground"
                : "text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
            )}
          >
            {isActive && (
              <motion.div
                layoutId={`${layoutGroupId}-active-nav`}
                className="absolute inset-0 rounded-md bg-sidebar-accent"
                transition={{ duration: 0.18, ease: "easeOut" }}
              />
            )}
            <span
              className={cn(
                "relative h-4 w-1 shrink-0 rounded-full transition-opacity",
                item.barColor,
                isActive ? "opacity-100" : "opacity-30",
              )}
              aria-hidden="true"
            />
            <Icon className="relative size-4 shrink-0" aria-hidden="true" />
            <span className="relative">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
