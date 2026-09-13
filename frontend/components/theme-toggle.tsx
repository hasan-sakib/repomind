"use client";

import { useTheme } from "@/components/theme-provider";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <label
      className="relative inline-flex h-5 w-[50px] shrink-0 cursor-pointer items-center"
      aria-label="Toggle dark mode"
    >
      <input
        type="checkbox"
        className="peer sr-only"
        checked={theme === "dark"}
        onChange={toggleTheme}
        suppressHydrationWarning
      />
      <span className="absolute inset-0 rounded-[5px] border-2 border-foreground bg-background shadow-[4px_4px_0_0_var(--foreground)] transition-colors duration-300 peer-checked:bg-brand" />
      <span className="absolute bottom-[2px] left-[-2px] size-5 rounded-[5px] border-2 border-foreground bg-background shadow-[0_3px_0_0_var(--foreground)] transition-transform duration-300 peer-checked:translate-x-[30px]" />
    </label>
  );
}
