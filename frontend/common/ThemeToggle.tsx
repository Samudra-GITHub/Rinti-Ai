"use client";

import { Moon, MoonStar } from "lucide-react";
import { useTheme } from "@/hooks/useTheme";
import { IconButton } from "@/ui/IconButton";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <IconButton
      icon={theme === "dark" ? Moon : MoonStar}
      onClick={toggleTheme}
      aria-label={`Switch to ${theme === "dark" ? "dim" : "dark"} theme`}
      active={theme === "dim"}
    />
  );
}
