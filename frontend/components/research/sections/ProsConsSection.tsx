"use client";

import { Plus, Minus } from "lucide-react";
import type { AnswerSectionDto } from "@/lib/research";
import { CitedText } from "@/components/research/CitedText";

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}
function asStringList(v: unknown): string[] {
  return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
}

export function ProsConsSection({ section }: { section: AnswerSectionDto }) {
  const items = section.items.filter(isPlainObject);
  if (items.length === 0) return null;

  return (
    <div className="glass-inset rounded-xl px-4 py-3.5">
      {section.title && <h3 className="mb-2.5 text-sm font-medium text-white/90">{section.title}</h3>}
      <div className="flex flex-col gap-3">
        {items.map((item, i) => {
          const name = (item.name ?? item.title ?? item.label ?? "") as string;
          const pros = asStringList(item.pros);
          const cons = asStringList(item.cons);
          return (
            <div key={i} className="rounded-lg border border-white/8 bg-white/[0.03] px-3 py-2.5">
              {name && <p className="mb-1.5 text-[13px] font-medium text-white/90">{name}</p>}
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <ul className="flex flex-col gap-1">
                  {pros.map((p, pi) => (
                    <li key={pi} className="flex items-start gap-1.5 text-[12px] text-white/70">
                      <Plus size={11} className="mt-0.5 shrink-0 text-cyan-300/70" />
                      <CitedText text={p} />
                    </li>
                  ))}
                </ul>
                <ul className="flex flex-col gap-1">
                  {cons.map((c, ci) => (
                    <li key={ci} className="flex items-start gap-1.5 text-[12px] text-white/70">
                      <Minus size={11} className="mt-0.5 shrink-0 text-amber-300/70" />
                      <CitedText text={c} />
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
