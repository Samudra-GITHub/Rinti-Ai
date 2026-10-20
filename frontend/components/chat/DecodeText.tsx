"use client";

import { useEffect, useState } from "react";
import { useReducedMotion } from "framer-motion";
import { useTheme } from "@/hooks/useTheme";

const GLYPHS = "abcdefghijklmnopqrstuvwxyz/\\|_-+";

interface DecodeTextProps {
  text: string;
  /** Milliseconds to wait before the letters start resolving. */
  delay?: number;
  /** Milliseconds for the whole line to resolve. */
  duration?: number;
  className?: string;
}

/**
 * A line of text that resolves from scrambled glyphs into its real letters,
 * left to right (the "decoding" paragraph in the reference). Screen readers
 * always get the final text, and reduced motion shows it immediately.
 */
export function DecodeText({ text, delay = 0, duration = 1100, className }: DecodeTextProps) {
  const systemReduced = useReducedMotion();
  const { reduceMotion } = useTheme();
  const still = Boolean(systemReduced) || reduceMotion;
  const [display, setDisplay] = useState(text);

  useEffect(() => {
    if (still) {
      setDisplay(text);
      return;
    }
    let frame = 0;
    let startedAt = 0;
    const timer = setTimeout(function begin() {
      startedAt = performance.now();
      const tick = (now: number) => {
        const progress = Math.min((now - startedAt) / duration, 1);
        const resolved = Math.floor(progress * text.length);
        setDisplay(
          text
            .split("")
            .map((char, index) =>
              index < resolved || char === " " ? char : GLYPHS[Math.floor(Math.random() * GLYPHS.length)]
            )
            .join("")
        );
        if (progress < 1) frame = requestAnimationFrame(tick);
        else setDisplay(text);
      };
      frame = requestAnimationFrame(tick);
    }, delay);

    return () => {
      clearTimeout(timer);
      cancelAnimationFrame(frame);
    };
  }, [text, delay, duration, still]);

  return (
    <span className={className} aria-label={text}>
      <span aria-hidden>{display}</span>
    </span>
  );
}
