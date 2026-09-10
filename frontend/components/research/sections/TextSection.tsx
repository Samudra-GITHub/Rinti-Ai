"use client";

import type { AnswerSectionDto } from "@/lib/research";
import { CitedText } from "@/components/research/CitedText";

/** Safe fallback for any section type the frontend doesn't specifically
 * recognize (R1.6B §2: unknown types render as plain text, never crash). */
export function TextSection({ section }: { section: AnswerSectionDto }) {
  const text = section.content || section.items.map((i) => (typeof i === "string" ? i : "")).join("\n");
  if (!text.trim()) return null;

  return (
    <div className="glass-inset rounded-xl px-4 py-3.5">
      {section.title && <h3 className="mb-1.5 text-sm font-medium text-white/90">{section.title}</h3>}
      <CitedText text={text} className="whitespace-pre-wrap text-[13px] leading-relaxed text-white/75" />
    </div>
  );
}
