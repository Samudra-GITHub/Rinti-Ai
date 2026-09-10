"use client";

import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import type { AnswerSectionDto, ResearchAnswerDto } from "@/lib/research";
import { CitedText } from "@/components/research/CitedText";
import { KeyFindingsSection } from "@/components/research/sections/KeyFindingsSection";
import { FactsSection } from "@/components/research/sections/FactsSection";
import { ResearchTable } from "@/components/research/sections/ResearchTable";
import { ComparisonSection } from "@/components/research/sections/ComparisonSection";
import { TimelineSection } from "@/components/research/sections/TimelineSection";
import { ProsConsSection } from "@/components/research/sections/ProsConsSection";
import { ProseSection } from "@/components/research/sections/ProseSection";
import { TextSection } from "@/components/research/sections/TextSection";

/**
 * Composes the whole structured research answer: title -> overview ->
 * executive summary -> typed sections in the order the backend produced
 * them. The application (this file) decides layout; the model only ever
 * supplied content within the fixed section-type vocabulary (R1.6B core
 * principle). Each section type has its own dedicated renderer — an
 * unrecognized type safely falls back to TextSection.
 */
function Section({ section }: { section: AnswerSectionDto }) {
  switch (section.type) {
    case "key_findings":
      return <KeyFindingsSection section={section} />;
    case "facts":
      return <FactsSection section={section} />;
    case "table":
      return <ResearchTable section={section} />;
    case "comparison":
      return <ComparisonSection section={section} />;
    case "timeline":
      return <TimelineSection section={section} />;
    case "pros_cons":
      return <ProsConsSection section={section} />;
    case "overview":
    case "summary":
    case "analysis":
    case "conflict":
    case "limitations":
      return <ProseSection section={section} />;
    case "sources":
      // Sources are never rendered from model content — the real SourcesPanel
      // (fed by backend-computed ResearchSource objects) covers this (R1.6B §10).
      return null;
    default:
      return <TextSection section={section} />;
  }
}

export function ResearchAnswerRenderer({ answer }: { answer: ResearchAnswerDto }) {
  const hasHeader = Boolean(answer.title || answer.overview || answer.executive_summary.length > 0);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="mx-auto flex w-full max-w-2xl flex-col gap-3"
    >
      {hasHeader && (
        <div className="glass-panel rounded-2xl px-5 py-4">
          {answer.title && (
            <h2 className="flex items-center gap-2 text-base font-semibold text-white/95">
              <Sparkles size={15} className="text-purple-300/80" />
              {answer.title}
            </h2>
          )}
          {answer.overview && (
            <CitedText
              text={answer.overview}
              className="mt-2 block whitespace-pre-wrap text-[13.5px] leading-relaxed text-white/70"
            />
          )}
          {answer.executive_summary.length > 0 && (
            <div className="mt-3 border-t border-white/8 pt-3">
              <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wider text-white/35">
                Executive Summary
              </p>
              <ul className="flex flex-col gap-1.5">
                {answer.executive_summary.map((finding, i) => (
                  <li key={i} className="flex items-start gap-2 text-[13px] leading-relaxed text-white/75">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-cyan-300/70" />
                    <CitedText text={finding} />
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {answer.sections.map((section, i) => (
        <Section key={i} section={section} />
      ))}
    </motion.div>
  );
}
