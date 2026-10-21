"use client";

import { SelectHTMLAttributes, forwardRef } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  "aria-label": string;
}

/** A native select (keyboard and screen-reader friendly) in the app's style. */
export const Select = forwardRef<HTMLSelectElement, SelectProps>(({ className, children, ...props }, ref) => (
  <span className="relative inline-flex">
    <select
      ref={ref}
      className={cn(
        "h-9 max-w-[16rem] cursor-pointer appearance-none rounded-full border border-fg/12 bg-fg/[0.04] pl-3.5 pr-9 text-[0.8rem] text-fg/85",
        "transition-colors duration-150 hover:border-fg/20 focus-ring disabled:cursor-not-allowed disabled:opacity-45",
        className
      )}
      {...props}
    >
      {children}
    </select>
    <ChevronDown size={14} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-fg/40" />
  </span>
));

Select.displayName = "Select";
