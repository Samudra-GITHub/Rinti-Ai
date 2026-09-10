"use client";

import type { AnswerSectionDto } from "@/lib/research";
import { CitedText } from "@/components/research/CitedText";

function isPlainObject(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function titleOf(item: Record<string, unknown>): string {
  const key = ["name", "title", "model", "item"].find((k) => typeof item[k] === "string");
  return key ? (item[key] as string) : Object.values(item).find((v) => typeof v === "string") as string ?? "";
}

export function ComparisonSection({ section }: { section: AnswerSectionDto }) {
  const items = section.items.filter(isPlainObject);
  if (items.length === 0) return null;

  return (
    <div className="glass-inset rounded-xl px-4 py-3.5">
      {section.title && <h3 className="mb-2.5 text-sm font-medium text-white/90">{section.title}</h3>}
      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2">
        {items.map((item, i) => {
          const heading = titleOf(item);
          const rest = Object.entries(item).filter(([, v]) => v !== heading && typeof v !== "object");
          return (
            <div key={i} className="rounded-lg border border-white/8 bg-white/[0.03] px-3 py-2.5">
              {heading && <p className="mb-1 text-[13px] font-medium text-white/90">{heading}</p>}
              {rest.map(([k, v]) => (
                <p key={k} className="text-[12px] leading-relaxed text-white/60">
                  <span className="capitalize text-white/40">{k.replace(/_/g, " ")}: </span>
                  <CitedText text={String(v)} />
                </p>
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}
