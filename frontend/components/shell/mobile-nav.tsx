"use client";

import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { NavList } from "@/components/shell/nav-items";
import { OrgSwitcher } from "@/components/shell/org-switcher";
import { useShell } from "@/components/shell/shell-context";

export function MobileNav() {
  const { mobileNavOpen, setMobileNavOpen } = useShell();

  return (
    <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
      <SheetContent side="left" className="w-64 p-0">
        <SheetHeader className="border-b border-sidebar-border px-2 py-0">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <div className="flex h-12 items-center">
            <OrgSwitcher />
          </div>
        </SheetHeader>
        <div className="flex-1 overflow-y-auto py-3">
          <NavList onNavigate={() => setMobileNavOpen(false)} layoutGroupId="mobile-nav" />
        </div>
      </SheetContent>
    </Sheet>
  );
}
