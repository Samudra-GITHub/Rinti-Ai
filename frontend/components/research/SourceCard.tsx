"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { ExternalLink, ChevronDown } from "lucide-react";
import type { ResearchSourceDto } from "@/lib/research";
import { cn } from "@/lib/cn";

const LABEL_STYLES: Record<string, string> = {
  Official: "border-purple-300/30 bg-purple-500/15 text-purple-200",
  Independent: "border-cyan-300/30 bg-cyan-500/15 text-cyan-200",
  "User-reported": "border-white/15 bg-white/5 text-white/60",
  "Low-confidence": "border-amber-300/25 bg-amber-500/10 text-amber-200/90",
  Recent: "border-cyan-300/25 bg-cyan-500/10 text-cyan-200/90",
  Older: "border-white/10 bg-white/5 text-white/45",
};

export function SourceCard({ source }: { source: ResearchSourceDto }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      id={`source-${source.n}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="glass-inset rounded-xl px-3 py-2.5"
    >
      <div className="flex items-start gap-2.5">
        <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-500/40 to-cyan-500/40 text-[11px] font-medium text-white/90">
          {source.n}
        </span>

        <div className="min-w-0 flex-1">
          <a
            href={source.url}
            target="_blank"
            rel="noopener noreferrer nofollow"
            className="group flex items-start gap-1.5 text-sm text-white/85 hover:text-white focus-ring"
          >
            <span className="line-clamp-2">{source.title}</span>
            <ExternalLink size={11} className="mt-1 shrink-0 text-white/30 group-hover:text-white/60" />
          </a>

          <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[11px] text-white/40">
            <span>{source.domain}</span>
            {source.publication_date && (
              <>
                <span aria-hidden>·</span>
                <span>{source.publication_date.slice(0, 10)}</span>
              </>
            )}
          </div>

          {source.labels.length > 0 && (
            <div className="mt-1.5 flex flex-wrap gap-1">
              {source.labels.map((label) => (
                <span
                  key={label}
                  className={cn(
                    "rounded-full border px-1.5 py-0.5 text-[10px]",
                    LABEL_STYLES[label] ?? "border-white/10 bg-white/5 text-white/50"
                  )}
                >
                  {label}
                </span>
              ))}
            </div>
          )}

          {source.excerpt && (
            <>
              <button
                onClick={() => setExpanded((v) => !v)}
                aria-expanded={expanded}
                className="mt-1.5 flex items-center gap-1 text-[11px] text-white/35 hover:text-white/70 focus-ring"
              >
                <ChevronDown
                  size={11}
                  className={cn("transition-transform", expanded && "rotate-180")}
                />
                {expanded ? "Hide excerpt" : "Show excerpt"}
              </button>
              {expanded && (
                <motion.p
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="mt-1.5 whitespace-pre-wrap text-[11px] leading-relaxed text-white/50"
                >
                  {source.excerpt}
                </motion.p>
              )}
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}
