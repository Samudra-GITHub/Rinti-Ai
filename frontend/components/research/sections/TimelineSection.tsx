"use client";

import type { AnswerSectionDto } from "@/lib/research";
import { CitedText } from "@/components/research/CitedText";

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

export function TimelineSection({ section }: { section: AnswerSectionDto }) {
  const items = section.items
    .map((raw) => {
      if (isPlainObject(raw)) {
        const date = (raw.date ?? raw.year ?? "") as string;
        const event = (raw.event ?? raw.title ?? raw.description ?? "") as string;
        return { date: String(date), event: String(event) };
      }
      return { date: "", event: String(raw) };
    })
    .filter((i) => i.event);
  if (items.length === 0) return null;

  return (
    <div className="glass-inset rounded-xl px-4 py-3.5">
      {section.title && <h3 className="mb-2.5 text-sm font-medium text-white/90">{section.title}</h3>}
      <ol className="relative ml-1.5 flex flex-col gap-3.5 border-l border-white/10 pl-4">
        {items.map((item, i) => (
          <li key={i} className="relative">
            <span className="absolute -left-[21px] top-1 h-2 w-2 rounded-full bg-gradient-to-br from-purple-400 to-cyan-400" />
            {item.date && <p className="text-[11px] font-medium text-white/45">{item.date}</p>}
            <CitedText text={item.event} className="text-[13px] leading-relaxed text-white/75" />
          </li>
        ))}
      </ol>
    </div>
  );
}
