"use client";

import { lazy, Suspense } from "react";
import { motion } from "framer-motion";
import { Check, Copy, Info, RotateCcw } from "lucide-react";
import { RintiOrb } from "@/components/orb/RintiOrb";
import { useCopyToClipboard } from "@/hooks/useCopyToClipboard";
import { useTheme } from "@/hooks/useTheme";
import { formatTime } from "@/lib/time";
import { cn } from "@/lib/cn";
import type { Message } from "@/types/conversation";

// Markdown + syntax highlighting is only needed once there is a conversation,
// so it stays out of the landing bundle.
const Markdown = lazy(() => import("./Markdown"));

interface ChatMessageProps {
  message: Message;
  /** This assistant message is still being generated. */
  isStreaming?: boolean;
  /** Offer "regenerate" on this message (only the latest reply, when idle). */
  canRegenerate?: boolean;
  onRegenerate?: () => void;
}

function ActionButton({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={label}
      title={label}
      className="flex h-7 items-center gap-1.5 rounded-md px-2 text-xs text-fg/45 transition-colors hover:bg-fg/8 hover:text-fg focus-ring"
    >
      {children}
    </button>
  );
}

export function ChatMessage({ message, isStreaming = false, canRegenerate = false, onRegenerate }: ChatMessageProps) {
  const { showTimestamps } = useTheme();
  const { copy, status } = useCopyToClipboard();
  const isUser = message.role === "user";
  const time = showTimestamps ? formatTime(message.timestamp) : "";

  if (message.role === "system") {
    return (
      <div className="mx-auto flex max-w-md items-center gap-2 rounded-full border border-fg/10 bg-fg/5 px-4 py-1.5 text-xs text-fg/55">
        <Info size={12} />
        {message.content}
      </div>
    );
  }

  if (isUser) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.22, ease: "easeOut" }}
        className="flex flex-col items-end gap-1"
      >
        <div className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md border border-fg/10 bg-fg/[0.06] px-4 py-2.5 text-[0.95rem] leading-relaxed text-fg">
          {message.content}
        </div>
        {time && <span className="px-1 text-[11px] text-fg/30">{time}</span>}
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="group flex gap-3.5"
    >
      <RintiOrb size="xs" active={isStreaming} className="mt-[0.3rem]" />
      <div className="min-w-0 flex-1">
        <Suspense fallback={<p className="whitespace-pre-wrap text-[0.97rem] leading-7 text-fg/90">{message.content}</p>}>
          <Markdown content={message.content} />
        </Suspense>

        {!isStreaming && message.content && (
          <div
            className={cn(
              "mt-2 -ml-2 flex items-center gap-0.5 transition-opacity duration-150",
              canRegenerate ? "opacity-100" : "opacity-0 focus-within:opacity-100 group-hover:opacity-100"
            )}
          >
            <ActionButton label={status === "copied" ? "Copied" : "Copy response"} onClick={() => copy(message.content)}>
              {status === "copied" ? <Check size={14} /> : <Copy size={14} />}
              {status === "copied" ? "Copied" : status === "failed" ? "Copy failed" : null}
            </ActionButton>
            {canRegenerate && onRegenerate && (
              <ActionButton label="Regenerate response" onClick={onRegenerate}>
                <RotateCcw size={14} />
              </ActionButton>
            )}
            {(time || message.answeredBy) && (
              <span className="ml-2 text-[11px] text-fg/30">
                {[time, message.answeredBy && `${message.answeredBy.kind === "local" ? "on this device" : "cloud"} · ${message.answeredBy.model}`]
                  .filter(Boolean)
                  .join(" · ")}
              </span>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}
