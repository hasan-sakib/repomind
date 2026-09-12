import { NavList } from "@/components/shell/nav-items";
import { OrgSwitcher } from "@/components/shell/org-switcher";

export function Sidebar() {
  return (
    <aside className="hidden w-56 shrink-0 flex-col border-r border-sidebar-border bg-sidebar lg:flex">
      <div className="flex h-12 items-center border-b border-sidebar-border px-2">
        <OrgSwitcher />
      </div>
      <div className="flex-1 overflow-y-auto py-3">
        <NavList />
      </div>
    </aside>
  );
}
