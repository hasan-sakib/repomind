import { CommandPalette } from "@/components/shell/command-palette";
import { MobileNav } from "@/components/shell/mobile-nav";
import { PageTransition } from "@/components/shell/page-transition";
import { ShellProvider } from "@/components/shell/shell-context";
import { Sidebar } from "@/components/shell/sidebar";
import { TopNav } from "@/components/shell/top-nav";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <ShellProvider>
      <div className="flex h-dvh min-h-0 w-full">
        <Sidebar />
        <MobileNav />
        <div className="flex min-w-0 flex-1 flex-col">
          <TopNav />
          <main className="min-h-0 flex-1 overflow-y-auto">
            <PageTransition>{children}</PageTransition>
          </main>
        </div>
      </div>
      <CommandPalette />
    </ShellProvider>
  );
}
