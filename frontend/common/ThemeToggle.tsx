"use client";

import { Moon, Sun } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { IconButton } from "@/ui/IconButton";

/** Quick light/dark switch. The full choice (including "system") lives in Settings. */
export function ThemeToggle() {
  const { resolvedTheme, setTheme } = useTheme();
  const next = resolvedTheme === "dark" ? "light" : "dark";

  return (
    <IconButton
      icon={resolvedTheme === "dark" ? Sun : Moon}
      appearance="bare"
      onClick={() => setTheme(next)}
      aria-label={`Switch to ${next} theme`}
      title={`Switch to ${next} theme`}
    />
  );
}
