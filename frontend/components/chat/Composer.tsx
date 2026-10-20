"use client";

import { forwardRef, useCallback, useEffect, useImperativeHandle, useRef } from "react";
import { ArrowUp, Square } from "lucide-react";
import { cn } from "@/lib/cn";

export interface ComposerHandle {
  focus: () => void;
}

interface ComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  onStop: () => void;
  isStreaming: boolean;
  placeholder: string;
  autoFocus?: boolean;
  /** Extra controls under the text field (e.g. the research toggle). */
  footer?: React.ReactNode;
  /** "hero" is the larger landing composer; "dock" sits at the bottom of a conversation. */
  size?: "hero" | "dock";
}

const MAX_LINES = 9;

/**
 * The message composer. Enter sends, Shift+Enter inserts a newline, and the
 * field grows with its content. While a reply is generating the send button
 * becomes Stop; typing the next message stays possible but sending waits.
 */
export const Composer = forwardRef<ComposerHandle, ComposerProps>(function Composer(
  { value, onChange, onSubmit, onStop, isStreaming, placeholder, autoFocus = false, footer, size = "dock" },
  ref
) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const canSend = value.trim().length > 0 && !isStreaming;

  useImperativeHandle(ref, () => ({ focus: () => textareaRef.current?.focus() }), []);

  // `field-sizing: content` (see globals.css) grows the field natively. Older
  // browsers ignore it, so size the field from its scroll height instead.
  const fitHeight = useCallback(() => {
    const el = textareaRef.current;
    if (!el || (typeof CSS !== "undefined" && CSS.supports("field-sizing", "content"))) return;
    el.style.height = "auto";
    const lineHeight = parseFloat(getComputedStyle(el).lineHeight) || 24;
    el.style.height = `${Math.min(el.scrollHeight, lineHeight * MAX_LINES)}px`;
  }, []);

  useEffect(() => {
    fitHeight();
  }, [value, fitHeight]);

  useEffect(() => {
    if (autoFocus) textareaRef.current?.focus();
  }, [autoFocus]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Don't send while an IME (Japanese, Chinese, ...) is still composing text.
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      if (canSend) onSubmit();
    }
  }

  return (
    <div
      onMouseDown={(e) => {
        // Clicking the padding around the field focuses it, without stealing clicks from buttons.
        if (e.target === e.currentTarget) {
          e.preventDefault();
          textareaRef.current?.focus();
        }
      }}
      className={cn(
        "group/composer edge-light relative cursor-text rounded-3xl border bg-surface/70 shadow-composer backdrop-blur-xl",
        "border-fg/12 transition-[border-color,box-shadow] duration-200",
        "focus-within:border-purple-400/45 focus-within:shadow-[0_0_0_4px_rgb(var(--p-500)/0.12),0_18px_50px_-24px_rgb(0_0_0/var(--shadow-strength))]",
        size === "hero" ? "px-5 pb-3 pt-4" : "px-4 pb-2.5 pt-3"
      )}
    >
      <div className="flex items-end gap-3">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          rows={1}
          aria-label="Message Rinti"
          placeholder={placeholder}
          enterKeyHint="send"
          className={cn(
            "composer-input min-w-0 flex-1 bg-transparent text-fg placeholder:text-fg/35 focus:outline-none",
            size === "hero" ? "py-1.5 text-[1.05rem] leading-7" : "py-1 text-[0.97rem] leading-6"
          )}
        />

        {isStreaming ? (
          <button
            type="button"
            onClick={onStop}
            aria-label="Stop generating"
            title="Stop generating"
            className="mb-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-fg text-bg transition-transform duration-150 hover:scale-105 active:scale-95 focus-ring"
          >
            <Square size={12} fill="currentColor" strokeWidth={0} />
          </button>
        ) : (
          <button
            type="button"
            onClick={onSubmit}
            disabled={!canSend}
            aria-label="Send message"
            title="Send (Enter)"
            className={cn(
              "mb-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition-[background-color,color,transform,opacity] duration-150 focus-ring",
              canSend
                ? "bg-accent text-on-accent hover:brightness-110 active:scale-95"
                : "bg-fg/8 text-fg/30"
            )}
          >
            <ArrowUp size={17} strokeWidth={2.2} />
          </button>
        )}
      </div>

      {footer && <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1.5">{footer}</div>}
    </div>
  );
});
