"use client";

import { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

interface ChipProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean;
  icon?: React.ReactNode;
}

export function Chip({ className, active = false, icon, children, ...props }: ChipProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition-all duration-200 focus-ring",
        active
          ? "border-purple-400/50 bg-purple-500/15 text-white shadow-glow-purple"
          : "border-white/10 bg-white/5 text-white/70 hover:border-white/20 hover:bg-white/10 hover:text-white",
        className
      )}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}
