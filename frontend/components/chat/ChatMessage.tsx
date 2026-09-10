"use client";

import { motion } from "framer-motion";
import { Sparkles, User, Info } from "lucide-react";
import { cn } from "@/lib/cn";
import type { Message } from "@/types/conversation";

interface ChatMessageProps {
  message: Message;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  if (isSystem) {
    return (
      <div className="mx-auto flex max-w-md items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs text-white/50">
        <Info size={12} />
        {message.content}
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={cn("flex w-full gap-3", isUser ? "flex-row-reverse" : "flex-row")}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border",
          isUser
            ? "border-cyan-300/30 bg-cyan-500/15 text-cyan-200"
            : "border-purple-300/30 bg-purple-500/15 text-purple-200"
        )}
      >
        {isUser ? <User size={15} /> : <Sparkles size={15} />}
      </div>

      <div
        className={cn(
          "glass max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed text-white/90",
          isUser ? "rounded-tr-sm" : "rounded-tl-sm"
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        <span className="mt-1.5 block text-[11px] text-white/35">
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>
    </motion.div>
  );
}
