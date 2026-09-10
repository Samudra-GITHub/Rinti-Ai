"use client";

import type { AnswerSectionDto } from "@/lib/research";
import { CitedText } from "@/components/research/CitedText";

export function ResearchTable({ section }: { section: AnswerSectionDto }) {
  if (section.columns.length === 0 || section.rows.length === 0) return null;

  return (
    <div className="glass-inset rounded-xl px-4 py-3.5">
      {section.title && <h3 className="mb-2 text-sm font-medium text-white/90">{section.title}</h3>}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[420px] border-collapse text-left text-[12.5px]">
          <thead>
            <tr className="border-b border-white/10">
              {section.columns.map((col, i) => (
                <th key={i} className="whitespace-nowrap px-2.5 py-2 font-medium text-white/50">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {section.rows.map((row, ri) => (
              <tr key={ri} className="border-b border-white/5 last:border-0">
                {row.map((cell, ci) => (
                  <td key={ci} className="px-2.5 py-2 align-top text-white/75">
                    <CitedText text={cell} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
