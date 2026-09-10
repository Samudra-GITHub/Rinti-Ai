"use client";

import { ButtonHTMLAttributes, forwardRef } from "react";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  icon: LucideIcon;
  size?: "sm" | "md" | "lg";
  active?: boolean;
  "aria-label": string;
}

const sizeClasses = {
  sm: "h-8 w-8",
  md: "h-10 w-10",
  lg: "h-12 w-12",
};

const iconSizes = {
  sm: 16,
  md: 18,
  lg: 20,
};

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ icon: Icon, size = "md", active = false, className, ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center rounded-full border transition-all duration-200 focus-ring",
          active
            ? "border-purple-400/50 bg-purple-500/15 text-white"
            : "border-white/10 bg-white/5 text-white/70 hover:border-white/20 hover:bg-white/10 hover:text-white",
          sizeClasses[size],
          className
        )}
        {...props}
      >
        <Icon size={iconSizes[size]} />
      </button>
    );
  }
);

IconButton.displayName = "IconButton";
