import { AuthBrandPanel } from "@/components/auth/auth-brand-panel";
import { ThemeToggle } from "@/components/theme-toggle";

export function SplitAuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative grid flex-1 grid-cols-1 lg:grid-cols-2">
      <div className="absolute right-4 top-4 z-10 lg:right-6 lg:top-6">
        <ThemeToggle />
      </div>
      <AuthBrandPanel />
      <div className="flex flex-col">{children}</div>
    </div>
  );
}
