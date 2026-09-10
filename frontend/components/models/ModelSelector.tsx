"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Check, ChevronDown } from "lucide-react";
import { useActiveModel } from "@/hooks/useActiveModel";
import { cn } from "@/lib/cn";

export function ModelSelector() {
  const { activeModel, setActiveModel, availableModels, isLoading, error } = useActiveModel();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  if (isLoading) {
    return <div className="glass rounded-full px-4 py-2 text-sm text-white/40">Loading models…</div>;
  }

  if (error || availableModels.length === 0) {
    return (
      <div className="glass rounded-full px-4 py-2 text-sm text-red-300/80">
        {error ?? "No model configured on the backend"}
      </div>
    );
  }

  return (
    <div ref={rootRef} className="relative inline-block">
      <button
        onClick={() => setOpen((prev) => !prev)}
        className="glass flex items-center gap-2.5 rounded-full py-2 pl-2.5 pr-3.5 text-sm text-white/85 transition-colors duration-200 hover:bg-white/10 focus-ring"
      >
        <span className="h-6 w-6 rounded-full bg-gradient-to-br from-purple-400 to-cyan-400" />
        <span className="max-w-[14rem] truncate">{activeModel ?? "Select a model"}</span>
        <ChevronDown size={14} className={cn("text-white/40 transition-transform", open && "rotate-180")} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -6, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.98 }}
            transition={{ duration: 0.15 }}
            className="glass-panel absolute left-0 top-full z-20 mt-2 w-64 rounded-2xl p-1.5"
          >
            {availableModels.map((m) => (
              <button
                key={m.id}
                onClick={() => {
                  setActiveModel(m.id);
                  setOpen(false);
                }}
                className={cn(
                  "flex w-full items-center gap-3 rounded-xl px-2.5 py-2 text-left text-sm transition-colors duration-200 hover:bg-white/8",
                  m.id === activeModel ? "text-white" : "text-white/65"
                )}
              >
                <span className="h-6 w-6 shrink-0 rounded-full bg-gradient-to-br from-purple-400 to-cyan-400" />
                <span className="min-w-0 flex-1">
                  <span className="block truncate leading-tight">{m.id}</span>
                  <span className="block text-[11px] text-white/35">{m.provider}</span>
                </span>
                {m.id === activeModel && <Check size={14} className="shrink-0 text-purple-300" />}
              </button>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
