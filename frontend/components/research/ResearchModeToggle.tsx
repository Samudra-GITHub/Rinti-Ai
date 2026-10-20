"use client";

import { Globe } from "lucide-react";
import { cn } from "@/lib/cn";

interface ResearchModeToggleProps {
  enabled: boolean;
  onToggle: (enabled: boolean) => void;
  available: boolean;
  disabled?: boolean;
}

export function ResearchModeToggle({
  enabled,
  onToggle,
  available,
  disabled = false,
}: ResearchModeToggleProps) {
  const unavailable = !available;
  const title = unavailable
    ? "Web research isn't configured on the server"
    : enabled
      ? "Research mode on: Rinti will search the web and cite sources"
      : "Turn on research mode to search the web";

  return (
    <button
      type="button"
      onClick={() => onToggle(!enabled)}
      disabled={disabled || unavailable}
      aria-pressed={enabled}
      title={title}
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-[background-color,border-color,color] duration-150 focus-ring",
        enabled
          ? "border-purple-400/40 bg-purple-500/15 text-purple-200"
          : "border-fg/10 text-fg/55 hover:border-fg/20 hover:bg-fg/6 hover:text-fg/85",
        (disabled || unavailable) && "cursor-not-allowed opacity-40 hover:bg-transparent"
      )}
    >
      <Globe size={13} />
      Research
    </button>
  );
}
