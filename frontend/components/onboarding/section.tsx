import { CheckCircle2Icon, CircleIcon, type LucideIcon } from "lucide-react";

import { cn } from "cn";

export function OnboardingSection({
  itemKey,
  icon: Icon,
  title,
  completed,
  onToggle,
  children,
}: {
  itemKey: string;
  icon: LucideIcon;
  title: string;
  completed: boolean;
  onToggle: (completed: boolean) => void;
  children: React.ReactNode;
}) {
  return (
    <section id={itemKey} className="scroll-mt-4 rounded-lg border border-border">
      <div className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
          <h2 className="text-sm font-semibold text-foreground">{title}</h2>
        </div>
        <button
          type="button"
          onClick={() => onToggle(!completed)}
          className={cn(
            "flex shrink-0 items-center gap-1.5 rounded-full border px-2 py-1 text-xs font-medium transition-colors",
            completed
              ? "border-success/30 bg-success/10 text-success"
              : "border-border text-muted-foreground hover:text-foreground",
          )}
        >
          {completed ? (
            <CheckCircle2Icon className="size-3.5" />
          ) : (
            <CircleIcon className="size-3.5" />
          )}
          {completed ? "Completed" : "Mark as complete"}
        </button>
      </div>
      <div className="space-y-4 p-4">{children}</div>
    </section>
  );
}
