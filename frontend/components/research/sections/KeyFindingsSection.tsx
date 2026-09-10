"use client";

import { Sparkle } from "lucide-react";
import type { AnswerSectionDto } from "@/lib/research";
import { CitedText } from "@/components/research/CitedText";

export function KeyFindingsSection({ section }: { section: AnswerSectionDto }) {
  const items = section.items.filter((i): i is string => typeof i === "string" && i.trim().length > 0);
  if (items.length === 0) return null;

  return (
    <div className="glass-inset rounded-xl px-4 py-3.5">
      {section.title && <h3 className="mb-2 text-sm font-medium text-white/90">{section.title}</h3>}
      <ul className="flex flex-col gap-2">
        {items.map((item, i) => (
          <li key={i} className="flex items-start gap-2 text-[13px] leading-relaxed text-white/75">
            <Sparkle size={12} className="mt-1 shrink-0 text-cyan-300/70" />
            <CitedText text={item} />
          </li>
        ))}
      </ul>
    </div>
  );
}
