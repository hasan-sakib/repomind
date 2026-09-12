"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "cn";

const TABS = [
  { label: "General", href: "/settings/general" },
  { label: "Members", href: "/settings/members" },
  { label: "Repositories", href: "/settings/repositories" },
  { label: "Security", href: "/settings/security" },
  { label: "Usage", href: "/settings/usage" },
  { label: "Billing", href: "/settings/billing" },
];

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="mx-auto max-w-2xl px-4 py-6 sm:px-6">
      <h1 className="mb-4 text-lg font-semibold tracking-tight">Settings</h1>
      <div className="mb-6 flex gap-1 border-b border-border">
        {TABS.map((tab) => {
          const isActive = pathname === tab.href;
          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={cn(
                "border-b-2 px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "border-brand text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground",
              )}
            >
              {tab.label}
            </Link>
          );
        })}
      </div>
      {children}
    </div>
  );
}
