"use client";

import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { RintiOrb } from "@/components/orb/RintiOrb";
import { PromptSuggestions } from "@/components/chat/PromptSuggestions";
import { ModelSelector } from "@/components/models/ModelSelector";

export default function HomePage() {
  const router = useRouter();

  function handleSelectPrompt(prompt: string) {
    router.push(`/chat?draft=${encodeURIComponent(prompt)}`);
  }

  return (
    <div className="mx-auto flex min-h-[calc(100vh-6rem)] max-w-3xl flex-col items-center justify-center gap-10 text-center">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
      >
        <RintiOrb size="xl" />
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.15 }}
        className="space-y-3"
      >
        <h1 className="text-3xl font-semibold tracking-tight text-white/95 sm:text-4xl">
          Meet <span className="text-gradient">Rinti</span>
        </h1>
        <p className="mx-auto max-w-md text-sm leading-relaxed text-white/50 sm:text-base">
          A calm, focused assistant. Pick a model, ask a question, or start from a suggestion.
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.25 }}
      >
        <ModelSelector />
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.35 }}
        className="w-full"
      >
        <PromptSuggestions onSelect={handleSelectPrompt} />
      </motion.div>
    </div>
  );
}
