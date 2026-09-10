"use client";

import { Fragment } from "react";

const CITATION_RE = /\[(\d{1,2})\]/g;

/**
 * Renders inline [n] citation markers as clickable chips that jump to the
 * matching SourceCard (id="source-N"). This is the ONLY place citation
 * markers get turned into UI — the model only ever writes the plain [n]
 * text; the frontend owns what that becomes visually (R1.6B §9/§10).
 */
export function CitedText({ text, className }: { text: string; className?: string }) {
  if (!text) return null;

  const parts: React.ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  CITATION_RE.lastIndex = 0;

  while ((match = CITATION_RE.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(<Fragment key={`t-${lastIndex}`}>{text.slice(lastIndex, match.index)}</Fragment>);
    }
    const n = match[1];
    parts.push(
      <button
        key={`c-${match.index}`}
        type="button"
        onClick={() => {
          document.getElementById(`source-${n}`)?.scrollIntoView({ behavior: "smooth", block: "center" });
        }}
        className="mx-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full border border-purple-300/30 bg-purple-500/15 px-1 align-super text-[9px] font-medium leading-none text-purple-200 transition-colors hover:bg-purple-500/30 focus-ring"
        aria-label={`Jump to source ${n}`}
      >
        {n}
      </button>
    );
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push(<Fragment key={`t-${lastIndex}`}>{text.slice(lastIndex)}</Fragment>);
  }

  return <span className={className}>{parts}</span>;
}
