"use client";

import { createContext, useContext, useEffect, useState } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "repomind-theme";

const ThemeContext = createContext<{ theme: Theme; toggleTheme: () => void } | null>(null);

/**
 * Always starts at "light" (matching SSR, where there's no `document` to
 * check) and corrects itself from the real `dark` class — already applied
 * to `<html>` pre-hydration by the anti-flash inline script in
 * app/layout.tsx — in an effect after mount. Reading that class straight
 * into the initial useState looks simpler, but React has a long-standing
 * hydration quirk where a controlled checkbox's `checked` DOM property
 * doesn't reliably sync during hydration itself — only on a later, ordinary
 * update. Deferring the correction to a post-mount effect (a real update,
 * not hydration) is what makes the toggle's knob position actually match
 * the theme on first load instead of sticking on "off".
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setTheme] = useState<Theme>("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setTheme(document.documentElement.classList.contains("dark") ? "dark" : "light");
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!mounted) return;
    document.documentElement.classList.toggle("dark", theme === "dark");
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // Private browsing / storage disabled — theme just won't persist.
    }
  }, [theme, mounted]);

  function toggleTheme() {
    setTheme((current) => (current === "dark" ? "light" : "dark"));
  }

  return <ThemeContext.Provider value={{ theme, toggleTheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme must be used within a ThemeProvider");
  return ctx;
}
