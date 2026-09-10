import { HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
}

export function Card({ className, hover = false, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "glass-panel rounded-xl2 p-5",
        hover && "transition-all duration-300 hover:border-white/20 hover:-translate-y-0.5 hover:shadow-glow-soft",
        className
      )}
      {...props}
    />
  );
}
