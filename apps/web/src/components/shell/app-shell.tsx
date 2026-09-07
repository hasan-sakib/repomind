import { CommandPalette } from "@/components/shell/command-palette";
import { MobileNav } from "@/components/shell/mobile-nav";
import { ShellProvider } from "@/components/shell/shell-context";
import { Sidebar } from "@/components/shell/sidebar";
import { TopNav } from "@/components/shell/top-nav";

export function AppShell({
  workspaceSlug,
  children,
}: {
  workspaceSlug: string;
  children: React.ReactNode;
}) {
  return (
    <ShellProvider>
      <div className="flex h-dvh min-h-0 w-full">
        <Sidebar workspaceSlug={workspaceSlug} />
        <MobileNav workspaceSlug={workspaceSlug} />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopNav workspaceSlug={workspaceSlug} />
          <main className="min-h-0 flex-1 overflow-y-auto">{children}</main>
        </div>
      </div>
      <CommandPalette workspaceSlug={workspaceSlug} />
    </ShellProvider>
  );
}
