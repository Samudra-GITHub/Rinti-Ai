"use client";

import { forwardRef } from "react";
import { motion } from "framer-motion";
import { ArrowUpRight } from "lucide-react";
import { promptSuggestions } from "@/lib/prompts";
import { RintiOrb } from "@/components/orb/RintiOrb";
import { CircuitTraces } from "./CircuitTraces";
import { DecodeText } from "./DecodeText";

const ease = [0.22, 1, 0.36, 1] as const;

/** Landing mark, wordmark and tagline, shown above the composer before the first message. */
export const Hero = forwardRef<HTMLDivElement>(function Hero(_, ref) {
  return (
    <motion.div
      ref={ref}
      exit={{ opacity: 0, y: -14, transition: { duration: 0.2, ease: "easeIn" } }}
      className="flex flex-col items-center px-4 pb-6 text-center sm:pb-8"
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.92 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.8, ease }}
        className="w-full"
      >
        <CircuitTraces>
          <RintiOrb size="md" />
        </CircuitTraces>
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, delay: 0.1, ease }}
        className="mt-2 font-display text-[clamp(3.5rem,10.5vw,6.75rem)] font-medium leading-[0.95] tracking-[-0.055em] text-fg"
      >
        Rinti
      </motion.h1>
      <motion.p
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, delay: 0.2, ease }}
        className="mt-1 text-[clamp(1rem,2.4vw,1.4rem)] font-medium tracking-tight text-purple-300"
      >
        ai/ClearAnswers
      </motion.p>
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.6, delay: 0.3 }}
        className="mt-4 text-sm text-fg/45"
      >
        <DecodeText text="Think clearly. Ask anything." delay={450} />
      </motion.p>
    </motion.div>
  );
});

interface SuggestionRowProps {
  onSelect: (prompt: string) => void;
}

export const SuggestionRow = forwardRef<HTMLDivElement, SuggestionRowProps>(function SuggestionRow(
  { onSelect },
  ref
) {
  return (
    <motion.div
      ref={ref}
      exit={{ opacity: 0, transition: { duration: 0.12 } }}
      className="mx-auto mt-4 grid w-full max-w-[44rem] grid-cols-2 gap-2.5 px-4 sm:grid-cols-4 sm:px-6"
    >
      {promptSuggestions.map((suggestion, index) => {
        const Icon = suggestion.icon;
        return (
          <motion.button
            key={suggestion.id}
            type="button"
            onClick={() => onSelect(suggestion.prompt)}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 + index * 0.07, ease }}
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.98 }}
            className="edge-light group relative flex flex-col items-start gap-2 rounded-2xl border border-fg/10 bg-surface/50 p-3 text-left backdrop-blur-md transition-[border-color,background-color] duration-150 hover:border-fg/20 hover:bg-surface/80 focus-ring"
          >
            <span className="flex h-7 w-7 items-center justify-center rounded-lg border border-fg/10 bg-fg/[0.05] text-purple-300">
              <Icon size={14} strokeWidth={1.9} />
            </span>
            <span className="text-[0.82rem] font-medium leading-tight text-fg/90">{suggestion.label}</span>
            <span className="hidden text-xs leading-snug text-fg/40 sm:block">{suggestion.description}</span>
            <span
              aria-hidden
              className="absolute right-2.5 top-2.5 flex h-6 w-6 items-center justify-center rounded-full border border-fg/10 text-fg/35 transition-colors duration-150 group-hover:border-purple-400/50 group-hover:text-purple-300"
            >
              <ArrowUpRight size={12} />
            </span>
          </motion.button>
        );
      })}
    </motion.div>
  );
});
