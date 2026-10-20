"use client";

import { ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

interface ChipProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  active?: boolean;
  icon?: React.ReactNode;
}

export function Chip({ className, active = false, icon, children, type = "button", ...props }: ChipProps) {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm transition-[background-color,border-color,color,transform] duration-150 active:scale-[0.98] focus-ring",
        active
          ? "border-purple-400/40 bg-purple-500/15 text-fg"
          : "border-fg/10 bg-fg/[0.04] text-fg/70 hover:border-fg/20 hover:bg-fg/8 hover:text-fg",
        className
      )}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}
