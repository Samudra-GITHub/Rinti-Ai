"use client";

import { motion } from "framer-motion";
import { Compass, Globe, BookOpen, GitCompare, PenLine } from "lucide-react";
import type { ResearchStage } from "@/lib/research";
import { cn } from "@/lib/cn";

const STAGES: { stage: ResearchStage; icon: typeof Compass; label: string }[] = [
  { stage: "planning", icon: Compass, label: "Planning research" },
  { stage: "searching", icon: Globe, label: "Searching the web" },
  { stage: "reading", icon: BookOpen, label: "Reading sources" },
  { stage: "cross_checking", icon: GitCompare, label: "Cross-checking evidence" },
  { stage: "writing", icon: PenLine, label: "Writing answer" },
];

interface ResearchProgressProps {
  stage: ResearchStage | null;
  label?: string;
  sourceCount: number;
}

export function ResearchProgress({ stage, label, sourceCount }: ResearchProgressProps) {
  if (!stage) return null;
  const activeIndex = STAGES.findIndex((s) => s.stage === stage);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-panel mx-auto flex max-w-2xl flex-col gap-3 rounded-2xl px-4 py-3"
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center gap-2 text-sm text-white/80">
        <motion.span
          animate={{ rotate: 360 }}
          transition={{ duration: 2.5, repeat: Infinity, ease: "linear" }}
          className="inline-flex"
        >
          <Globe size={14} className="text-cyan-300" />
        </motion.span>
        {label ?? STAGES[Math.max(activeIndex, 0)].label}
        {sourceCount > 0 && (
          <span className="text-xs text-white/40">
            · {sourceCount} source{sourceCount === 1 ? "" : "s"}
          </span>
        )}
      </div>

      <div className="flex items-center gap-1.5">
        {STAGES.map((s, index) => {
          const done = index < activeIndex;
          const active = index === activeIndex;
          return (
            <div key={s.stage} className="flex flex-1 flex-col gap-1">
              <div
                className={cn(
                  "h-0.5 rounded-full transition-colors duration-500",
                  done && "bg-cyan-400/60",
                  active && "bg-gradient-to-r from-purple-400 to-cyan-400",
                  !done && !active && "bg-white/10"
                )}
              />
              <span
                className={cn(
                  "hidden text-[10px] transition-colors duration-300 sm:block",
                  active ? "text-white/60" : "text-white/25"
                )}
              >
                {s.label.split(" ")[0]}
              </span>
            </div>
          );
        })}
      </div>
    </motion.div>
  );
}
