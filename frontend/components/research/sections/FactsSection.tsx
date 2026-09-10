"use client";

import { Check } from "lucide-react";
import type { AnswerSectionDto } from "@/lib/research";
import { CitedText } from "@/components/research/CitedText";
import { StatusBadge } from "@/components/research/StatusBadge";
import { cn } from "@/lib/cn";

/**
 * One status-labeled fact list — e.g. "Confirmed / Official" vs "Rumored /
 * Unconfirmed" render as two separate FactsSection instances (R1.6B §4:
 * never blend them into one list without a status field).
 */
export function FactsSection({ section }: { section: AnswerSectionDto }) {
  const items = section.items.filter((i): i is string => typeof i === "string" && i.trim().length > 0);
  if (items.length === 0) return null;

  const isUncertain = section.status === "RUMORED" || section.status === "SPECULATIVE";

  return (
    <div
      className={cn(
        "rounded-xl border px-4 py-3.5",
        isUncertain ? "border-amber-300/20 bg-amber-500/5" : "glass-inset"
      )}
    >
      <div className="mb-2 flex items-center gap-2">
        {section.title && <h3 className="text-sm font-medium text-white/90">{section.title}</h3>}
        {section.status && <StatusBadge status={section.status} />}
      </div>
      <ul className="flex flex-col gap-1.5">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-[13px] leading-relaxed text-white/75">
            <Check size={12} className={cn("mt-1 shrink-0", isUncertain ? "text-amber-300/60" : "text-cyan-300/70")} />
            <CitedText text={item} />
          </li>
        ))}
      </ul>
    </div>
  );
}
