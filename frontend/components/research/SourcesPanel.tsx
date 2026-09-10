"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Library, ChevronDown, AlertTriangle } from "lucide-react";
import type { ResearchSourceDto } from "@/lib/research";
import { SourceCard } from "./SourceCard";
import { cn } from "@/lib/cn";

interface SourcesPanelProps {
  sources: ResearchSourceDto[];
  notes?: string[];
  defaultOpen?: boolean;
}

export function SourcesPanel({ sources, notes = [], defaultOpen = true }: SourcesPanelProps) {
  const [open, setOpen] = useState(defaultOpen);
  if (sources.length === 0) return null;

  return (
    <div className="glass-panel rounded-2xl px-3 py-2.5">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 text-left text-xs font-medium uppercase tracking-wider text-white/45 hover:text-white/70 focus-ring"
      >
        <Library size={13} />
        {sources.length} source{sources.length === 1 ? "" : "s"}
        <ChevronDown
          size={13}
          className={cn("ml-auto transition-transform", open && "rotate-180")}
        />
      </button>

      {notes.length > 0 && (
        <div className="mt-2 flex flex-col gap-1">
          {notes.map((note) => (
            <p
              key={note}
              className="flex items-start gap-1.5 rounded-lg border border-amber-300/20 bg-amber-500/10 px-2 py-1.5 text-[11px] text-amber-200/90"
            >
              <AlertTriangle size={11} className="mt-0.5 shrink-0" />
              {note}
            </p>
          ))}
        </div>
      )}

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-2 space-y-1.5 overflow-hidden"
          >
            {sources.map((source) => (
              <SourceCard key={source.id} source={source} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
