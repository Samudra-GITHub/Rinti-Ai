"use client";

import { useContext } from "react";
import { ThemeContext } from "@/providers/ThemeProvider";

/** Theme + display preferences (theme, reduced motion, timestamps). */
export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error("useTheme must be used within a ThemeProvider");
  }
  return ctx;
}
