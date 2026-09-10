"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/cn";

type OrbSize = "sm" | "md" | "lg" | "xl";

interface RintiOrbProps {
  size?: OrbSize;
  active?: boolean;
  className?: string;
}

const sizeMap: Record<OrbSize, string> = {
  sm: "h-10 w-10",
  md: "h-16 w-16",
  lg: "h-28 w-28",
  xl: "h-44 w-44",
};

export function RintiOrb({ size = "lg", active = false, className }: RintiOrbProps) {
  return (
    <div className={cn("relative flex items-center justify-center", sizeMap[size], className)}>
      <div className="absolute inset-[-40%] rounded-full bg-aura-gradient blur-2xl" />

      <motion.div
        className="absolute inset-0 rounded-full border border-purple-300/20"
        animate={{ rotate: 360 }}
        transition={{ duration: 18, repeat: Infinity, ease: "linear" }}
      />
      <motion.div
        className="absolute inset-[10%] rounded-full border border-cyan-300/20"
        animate={{ rotate: -360 }}
        transition={{ duration: 26, repeat: Infinity, ease: "linear" }}
      />

      <motion.div
        className="absolute inset-[15%] rounded-full bg-orb-gradient shadow-glow-purple"
        animate={
          active
            ? { scale: [1, 1.15, 1], opacity: [0.9, 1, 0.9] }
            : { scale: [1, 1.06, 1], opacity: [0.85, 1, 0.85] }
        }
        transition={{
          duration: active ? 1.1 : 4.5,
          repeat: Infinity,
          ease: "easeInOut",
        }}
        whileHover={{ scale: 1.08 }}
      />

      <motion.div
        className="absolute inset-[32%] rounded-full bg-white/80 blur-[2px]"
        animate={{ opacity: [0.5, 0.85, 0.5] }}
        transition={{ duration: active ? 0.9 : 3.2, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}
