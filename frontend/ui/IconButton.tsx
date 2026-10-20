"use client";

import { ButtonHTMLAttributes, forwardRef } from "react";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: LucideIcon;
  size?: "sm" | "md" | "lg";
  active?: boolean;
  /** "bare" has no resting border (for dense toolbars); "outline" is the default. */
  appearance?: "outline" | "bare";
  "aria-label": string;
}

const sizeClasses = {
  sm: "h-8 w-8",
  md: "h-10 w-10",
  lg: "h-12 w-12",
};

const iconSizes = {
  sm: 15,
  md: 17,
  lg: 20,
};

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  (
    { icon: Icon, size = "md", active = false, appearance = "outline", type = "button", className, ...props },
    ref
  ) => {
    return (
      <button
        ref={ref}
        type={type}
        className={cn(
          "inline-flex shrink-0 items-center justify-center rounded-full border transition-[background-color,border-color,color,transform,opacity] duration-150 active:scale-95 disabled:pointer-events-none disabled:opacity-40 focus-ring",
          active
            ? "border-purple-400/40 bg-purple-500/15 text-fg"
            : appearance === "outline"
              ? "border-fg/10 bg-fg/[0.04] text-fg/65 hover:border-fg/20 hover:bg-fg/10 hover:text-fg"
              : "border-transparent text-fg/55 hover:bg-fg/8 hover:text-fg",
          sizeClasses[size],
          className
        )}
        {...props}
      >
        <Icon size={iconSizes[size]} strokeWidth={1.8} />
      </button>
    );
  }
);

IconButton.displayName = "IconButton";
