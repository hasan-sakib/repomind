import { NavList } from "@/components/shell/nav-items";
import { WorkspaceSwitcher } from "@/components/shell/workspace-switcher";

export function Sidebar({ workspaceSlug }: { workspaceSlug: string }) {
  return (
    <aside className="hidden w-56 shrink-0 flex-col border-r border-sidebar-border bg-sidebar lg:flex">
      <div className="flex h-12 items-center border-b border-sidebar-border px-2">
        <WorkspaceSwitcher activeSlug={workspaceSlug} />
      </div>
      <div className="flex-1 overflow-y-auto py-3">
        <NavList workspaceSlug={workspaceSlug} />
      </div>
    </aside>
  );
}
