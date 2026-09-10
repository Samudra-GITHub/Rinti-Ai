// Research types + client. Mirrors lib/api.ts conventions: the browser only ever
// sees the safe, pre-computed source shape the backend chooses to expose — never
// raw page content, plans, prompts, or provider payloads. Calls go same-origin
// through app/api/[...path]/route.ts, same reasoning as lib/api.ts (that's what
// carries the session cookie to the backend).
import { withCsrfHeader } from "@/lib/http";

export type ResearchMode = "QUICK" | "STANDARD";

export type ResearchIntent =
  | "NO_RESEARCH"
  | "CURRENT_INFORMATION"
  | "FACT_CHECK"
  | "COMPARISON"
  | "PRODUCT_RESEARCH"
  | "NEWS_RESEARCH"
  | "GENERAL_RESEARCH";

export type SourceType =
  | "OFFICIAL"
  | "INDUSTRY"
  | "ACADEMIC"
  | "NEWS"
  | "USER_REPORTED"
  | "RUMOR"
  | "OTHER";

export interface ResearchSourceDto {
  n: number;
  id: string;
  url: string;
  title: string;
  domain: string;
  publisher: string | null;
  source_type?: SourceType;
  status?: string;
  confidence?: "HIGH" | "MEDIUM" | "LOW";
  publication_date: string | null;
  retrieved_at?: string | null;
  labels: string[];
  excerpt: string;
}

/** R1.6B structured answer types. The backend controls which `type` values
 * exist; anything this union doesn't recognize renders as plain text. */
export type SectionType =
  | "overview"
  | "summary"
  | "key_findings"
  | "table"
  | "comparison"
  | "timeline"
  | "pros_cons"
  | "facts"
  | "analysis"
  | "conflict"
  | "limitations"
  | "sources"
  | "text";

export type FactStatus = "OFFICIAL" | "CONFIRMED" | "REPORTED" | "RUMORED" | "SPECULATIVE";

export interface AnswerSectionDto {
  type: SectionType;
  title: string;
  content: string;
  items: unknown[];
  columns: string[];
  rows: string[][];
  status: FactStatus | null;
}

export interface ResearchAnswerDto {
  title: string;
  query: string;
  overview: string;
  executive_summary: string[];
  sections: AnswerSectionDto[];
}

export interface ResearchStatusDto {
  available: boolean;
  provider: string | null;
  modes: ResearchMode[];
}

export interface IntentDto {
  intent: ResearchIntent;
  needs_research: boolean;
  requires_freshness: boolean;
  reason: string;
}

/** High-level stages the backend reports. Never chain-of-thought. */
export type ResearchStage =
  | "planning"
  | "searching"
  | "reading"
  | "cross_checking"
  | "writing";

export interface ResearchStatusEvent {
  stage: ResearchStage;
  progress: number;
  label: string;
}

export interface ResearchDoneEvent {
  sessionId: string;
  partial: boolean;
  notes: string[];
  usage: Record<string, number>;
}

export async function fetchResearchStatus(): Promise<ResearchStatusDto> {
  const res = await fetch("/api/research/status", {
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) throw new Error("Could not check research availability");
  return (await res.json()) as ResearchStatusDto;
}

export interface ResearchSessionDto {
  id: string;
  query: string;
  result: {
    sources?: ResearchSourceDto[];
    notes?: string[];
    structured_answer?: ResearchAnswerDto | null;
  };
}

/** Rehydrates the sources panel for a persisted research turn after refresh. */
export async function fetchResearchSession(sessionId: string): Promise<ResearchSessionDto | null> {
  try {
    const res = await fetch(`/api/research/${sessionId}`, {
      headers: { "Content-Type": "application/json" },
    });
    if (!res.ok) return null;
    return (await res.json()) as ResearchSessionDto;
  } catch {
    return null;
  }
}

export async function detectIntent(query: string): Promise<IntentDto | null> {
  try {
    const res = await fetch("/api/research/intent", {
      method: "POST",
      headers: withCsrfHeader({ "Content-Type": "application/json" }),
      body: JSON.stringify({ query }),
    });
    if (!res.ok) return null;
    return (await res.json()) as IntentDto;
  } catch {
    return null;
  }
}
