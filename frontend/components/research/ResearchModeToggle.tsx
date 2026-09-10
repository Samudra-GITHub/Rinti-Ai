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
      ? "Research mode on — Rinti will search the web and cite sources"
      : "Turn on research mode to search the web";

  return (
    <button
      type="button"
      onClick={() => onToggle(!enabled)}
      disabled={disabled || unavailable}
      aria-pressed={enabled}
      aria-label="Toggle research mode"
      title={title}
      className={cn(
        "inline-flex shrink-0 items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs transition-all duration-200 focus-ring",
        enabled
          ? "border-cyan-300/40 bg-cyan-500/15 text-cyan-100 shadow-glow-cyan"
          : "border-white/10 bg-white/5 text-white/55 hover:border-white/20 hover:text-white/85",
        (disabled || unavailable) && "cursor-not-allowed opacity-40"
      )}
    >
      <Globe size={13} />
      Research
    </button>
  );
}
