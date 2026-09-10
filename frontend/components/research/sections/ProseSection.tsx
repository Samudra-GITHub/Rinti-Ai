"use client";

import { AlertTriangle, GitCompareArrows, ScanText } from "lucide-react";
import type { AnswerSectionDto } from "@/lib/research";
import { CitedText } from "@/components/research/CitedText";
import { cn } from "@/lib/cn";

/**
 * Shared renderer for the plain title+paragraph section types: overview,
 * summary, analysis, conflict, limitations. They differ only in tone/icon —
 * all just need a heading and a CitedText paragraph.
 */
export function ProseSection({ section }: { section: AnswerSectionDto }) {
  if (!section.content) return null;

  const isConflict = section.type === "conflict";
  const isLimitations = section.type === "limitations";

  return (
    <div
      className={cn(
        "rounded-xl border px-4 py-3.5",
        isConflict
          ? "border-amber-300/20 bg-amber-500/5"
          : isLimitations
            ? "border-white/10 bg-white/[0.03]"
            : "glass-inset"
      )}
    >
      {section.title && (
        <h3 className="mb-1.5 flex items-center gap-1.5 text-sm font-medium text-white/90">
          {isConflict && <GitCompareArrows size={13} className="text-amber-300/80" />}
          {isLimitations && <AlertTriangle size={13} className="text-white/40" />}
          {!isConflict && !isLimitations && <ScanText size={13} className="text-purple-300/70" />}
          {section.title}
        </h3>
      )}
      <CitedText
        text={section.content}
        className="whitespace-pre-wrap text-[13px] leading-relaxed text-white/75"
      />
    </div>
  );
}
