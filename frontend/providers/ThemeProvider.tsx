"use client";

import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import { MotionConfig } from "framer-motion";

export type ThemePreference = "system" | "light" | "dark";
export type ResolvedTheme = "light" | "dark";

interface PreferencesContextValue {
  /** What the user picked: follow the system, or force light/dark. */
  theme: ThemePreference;
  /** What is actually applied right now. */
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: ThemePreference) => void;
  reduceMotion: boolean;
  setReduceMotion: (value: boolean) => void;
  showTimestamps: boolean;
  setShowTimestamps: (value: boolean) => void;
}

export const ThemeContext = createContext<PreferencesContextValue | null>(null);

// The same keys are read by the inline script in app/layout.tsx so the first
// paint already has the right theme.
const THEME_KEY = "rinti-theme";
const MOTION_KEY = "rinti-reduce-motion";
const TIMESTAMPS_KEY = "rinti-timestamps";

function readStorage(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null; // storage can be unavailable (private mode, blocked site data)
  }
}

function writeStorage(key: string, value: string) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    // ignore unavailable storage
  }
}

function systemTheme(): ResolvedTheme {
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemePreference>("system");
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>("dark");
  const [reduceMotion, setReduceMotionState] = useState(false);
  const [showTimestamps, setShowTimestampsState] = useState(true);

  // Load saved preferences once on the client.
  useEffect(() => {
    const stored = readStorage(THEME_KEY);
    if (stored === "light" || stored === "dark" || stored === "system") setThemeState(stored);
    setReduceMotionState(readStorage(MOTION_KEY) === "1");
    setShowTimestampsState(readStorage(TIMESTAMPS_KEY) !== "0");
  }, []);

  // Apply the theme, and follow the OS when the preference is "system".
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: light)");
    const apply = () => {
      const next: ResolvedTheme = theme === "system" ? systemTheme() : theme;
      document.documentElement.dataset.theme = next;
      setResolvedTheme(next);
    };
    apply();
    if (theme !== "system") return;
    media.addEventListener("change", apply);
    return () => media.removeEventListener("change", apply);
  }, [theme]);

  useEffect(() => {
    if (reduceMotion) document.documentElement.dataset.motion = "reduce";
    else delete document.documentElement.dataset.motion;
  }, [reduceMotion]);

  const setTheme = useCallback((next: ThemePreference) => {
    setThemeState(next);
    writeStorage(THEME_KEY, next);
  }, []);
  const setReduceMotion = useCallback((value: boolean) => {
    setReduceMotionState(value);
    writeStorage(MOTION_KEY, value ? "1" : "0");
  }, []);
  const setShowTimestamps = useCallback((value: boolean) => {
    setShowTimestampsState(value);
    writeStorage(TIMESTAMPS_KEY, value ? "1" : "0");
  }, []);

  const value = useMemo(
    () => ({
      theme,
      resolvedTheme,
      setTheme,
      reduceMotion,
      setReduceMotion,
      showTimestamps,
      setShowTimestamps,
    }),
    [theme, resolvedTheme, setTheme, reduceMotion, setReduceMotion, showTimestamps, setShowTimestamps]
  );

  return (
    <ThemeContext.Provider value={value}>
      {/* "user" follows the OS reduced-motion setting; the in-app switch forces it. */}
      <MotionConfig reducedMotion={reduceMotion ? "always" : "user"}>{children}</MotionConfig>
    </ThemeContext.Provider>
  );
}
