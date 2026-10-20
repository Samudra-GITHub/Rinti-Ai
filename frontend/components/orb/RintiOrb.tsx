"use client";

import { motion } from "framer-motion";
import { Asterisk } from "lucide-react";
import { cn } from "@/lib/cn";

type MarkSize = "xs" | "sm" | "md" | "lg";

interface RintiOrbProps {
  size?: MarkSize;
  /** Pulses a soft ring while Rinti is working. Respects reduced motion via MotionConfig. */
  active?: boolean;
  className?: string;
}

const boxSize: Record<MarkSize, string> = {
  xs: "h-6 w-6 rounded-[0.45rem]",
  sm: "h-8 w-8 rounded-[0.6rem]",
  md: "h-12 w-12 rounded-2xl",
  lg: "h-16 w-16 rounded-[1.25rem]",
};

const iconSize: Record<MarkSize, number> = { xs: 13, sm: 17, md: 24, lg: 32 };

/**
 * The Rinti mark: an asterisk on a small glass tile with a faint green glow,
 * the node the reference's circuit traces lead out of. (The file keeps its old
 * name so existing imports stay valid.)
 */
export function RintiOrb({ size = "sm", active = false, className }: RintiOrbProps) {
  return (
    <div
      aria-hidden
      className={cn(
        "relative flex shrink-0 items-center justify-center border border-fg/15 bg-fg/[0.07]",
        "shadow-[inset_0_1px_0_0_rgb(var(--fg)/0.14),0_0_20px_-6px_rgb(var(--accent)/0.55)]",
        boxSize[size],
        className
      )}
    >
      <Asterisk size={iconSize[size]} strokeWidth={2.4} className="text-fg" />
      {active && (
        <motion.span
          className="absolute inset-0 rounded-[inherit] border border-purple-300/60"
          initial={{ opacity: 0.7, scale: 1 }}
          animate={{ opacity: 0, scale: 1.55 }}
          transition={{ duration: 1.4, repeat: Infinity, ease: "easeOut" }}
        />
      )}
    </div>
  );
}
