"use client";

import { createContext, useCallback, useEffect, useMemo, useState } from "react";

export type Theme = "dark" | "dim";

interface ThemeContextValue {
  theme: Theme;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
}

export const ThemeContext = createContext<ThemeContextValue | null>(null);

const STORAGE_KEY = "rinti-theme";

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<Theme>("dark");

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY) as Theme | null;
      if (stored === "dark" || stored === "dim") {
        setThemeState(stored);
      }
    } catch {
      // ignore unavailable storage
    }
  }, []);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove("dark", "dim");
    root.classList.add(theme);
    try {
      window.localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // ignore unavailable storage
    }
  }, [theme]);

  const setTheme = useCallback((next: Theme) => setThemeState(next), []);
  const toggleTheme = useCallback(
    () => setThemeState((prev) => (prev === "dark" ? "dim" : "dark")),
    []
  );

  const value = useMemo(
    () => ({ theme, setTheme, toggleTheme }),
    [theme, setTheme, toggleTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
