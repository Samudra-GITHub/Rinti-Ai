import { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
}

export function Card({ className, hover = false, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-2xl border border-fg/10 bg-surface/70 p-5",
        hover && "transition-[border-color,background-color] duration-200 hover:border-fg/20 hover:bg-surface",
        className
      )}
      {...props}
    />
  );
}
