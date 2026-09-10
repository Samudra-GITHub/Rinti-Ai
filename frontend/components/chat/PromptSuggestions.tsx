"use client";

import { motion } from "framer-motion";
import { Sparkle } from "lucide-react";
import { promptSuggestions } from "@/lib/prompts";
import { Chip } from "@/ui/Chip";
import { cn } from "@/lib/cn";

interface PromptSuggestionsProps {
  onSelect: (prompt: string) => void;
  className?: string;
}

export function PromptSuggestions({ onSelect, className }: PromptSuggestionsProps) {
  return (
    <div className={cn("flex flex-wrap items-center justify-center gap-2.5", className)}>
      {promptSuggestions.map((suggestion, index) => (
        <motion.div
          key={suggestion.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: index * 0.05, ease: "easeOut" }}
        >
          <Chip icon={<Sparkle size={13} />} onClick={() => onSelect(suggestion.prompt)}>
            {suggestion.label}
          </Chip>
        </motion.div>
      ))}
    </div>
  );
}
