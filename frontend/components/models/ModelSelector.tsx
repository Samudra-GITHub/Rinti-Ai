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
    if (!open) return;
    function handlePointer(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handlePointer);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handlePointer);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  if (isLoading) {
    return <div className="h-9 w-32 animate-pulse rounded-full bg-fg/[0.06]" aria-hidden />;
  }

  if (error || availableModels.length === 0) {
    return (
      <div
        role="status"
        className="rounded-full border border-red-500/25 bg-red-500/10 px-3 py-1.5 text-xs text-red-700 dark:text-red-300"
      >
        {error ?? "No model is configured on the server"}
      </div>
    );
  }

  return (
    <div ref={rootRef} className="relative inline-block min-w-0">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="flex h-9 max-w-full items-center gap-2 rounded-full border border-fg/10 bg-fg/[0.04] pl-3 pr-2.5 text-[0.8rem] text-fg/75 backdrop-blur transition-colors duration-150 hover:border-purple-400/30 hover:text-fg focus-ring"
      >
        <span aria-hidden className="h-1.5 w-1.5 shrink-0 rounded-full bg-accent shadow-[0_0_8px_rgb(var(--accent)/0.9)]" />
        <span className="max-w-[12rem] truncate">{activeModel ?? "Select a model"}</span>
        <ChevronDown size={14} className={cn("shrink-0 text-fg/40 transition-transform duration-200", open && "rotate-180")} />
      </button>

      <AnimatePresence>
        {open && (
          <motion.ul
            role="listbox"
            aria-label="Model"
            initial={{ opacity: 0, y: -4, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -4, scale: 0.98 }}
            transition={{ duration: 0.14 }}
            className="absolute left-0 top-full z-30 mt-2 w-72 max-w-[calc(100vw-1.5rem)] origin-top-left rounded-2xl border border-fg/10 bg-elevated p-1.5 shadow-composer"
          >
            {availableModels.map((m) => (
              <li key={m.id} role="option" aria-selected={m.id === activeModel}>
                <button
                  type="button"
                  onClick={() => {
                    setActiveModel(m.id);
                    setOpen(false);
                  }}
                  className={cn(
                    "flex w-full items-center gap-3 rounded-xl px-2.5 py-2 text-left text-sm transition-colors duration-150 hover:bg-fg/6 focus-ring",
                    m.id === activeModel ? "text-fg" : "text-fg/65"
                  )}
                >
                  <span className="min-w-0 flex-1">
                    <span className="block truncate leading-tight">{m.id}</span>
                    <span className="block text-[11px] text-fg/35">{m.provider}</span>
                  </span>
                  {m.id === activeModel && <Check size={14} className="shrink-0 text-purple-300" />}
                </button>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}
