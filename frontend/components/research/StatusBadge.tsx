"use client";

import { ShieldCheck, CircleCheck, Newspaper, HelpCircle, Sparkles } from "lucide-react";
import type { FactStatus } from "@/lib/research";
import { cn } from "@/lib/cn";

const STATUS_STYLE: Record<FactStatus, { label: string; className: string; icon: typeof ShieldCheck }> = {
  OFFICIAL: { label: "Official", className: "border-purple-300/30 bg-purple-500/15 text-purple-200", icon: ShieldCheck },
  CONFIRMED: { label: "Confirmed", className: "border-cyan-300/30 bg-cyan-500/15 text-cyan-200", icon: CircleCheck },
  REPORTED: { label: "Reported", className: "border-white/15 bg-white/5 text-white/65", icon: Newspaper },
  RUMORED: { label: "Rumored", className: "border-amber-300/30 bg-amber-500/10 text-amber-200", icon: HelpCircle },
  SPECULATIVE: { label: "Speculative", className: "border-amber-300/20 bg-amber-500/5 text-amber-200/80", icon: Sparkles },
};

export function StatusBadge({ status, className }: { status: FactStatus; className?: string }) {
  const style = STATUS_STYLE[status];
  if (!style) return null;
  const Icon = style.icon;
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium",
        style.className,
        className
      )}
    >
      <Icon size={10} />
      {style.label}
    </span>
  );
}
