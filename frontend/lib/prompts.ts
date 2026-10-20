import { BookOpen, Code2, PenLine, Route, type LucideIcon } from "lucide-react";

export interface PromptSuggestion {
  id: string;
  label: string;
  /** One muted line shown under the title on larger screens. */
  description: string;
  prompt: string;
  icon: LucideIcon;
}

// Complete, ready-to-send prompts: choosing one fills the composer so it can be
// sent as is or edited first.
export const promptSuggestions: PromptSuggestion[] = [
  {
    id: "learn",
    label: "Explain something",
    description: "Any topic, in plain language.",
    prompt: "Explain how vaccines train the immune system, as if I'm curious but new to biology.",
    icon: BookOpen,
  },
  {
    id: "write",
    label: "Help me write",
    description: "Emails, notes, a first draft.",
    prompt: "Help me write a short, polite email asking my manager for a one-week deadline extension.",
    icon: PenLine,
  },
  {
    id: "code",
    label: "Debug some code",
    description: "Find the bug and the fix.",
    prompt: "Why does removing items from a Python list while looping over it skip some elements? Show a fix.",
    icon: Code2,
  },
  {
    id: "plan",
    label: "Plan my week",
    description: "Priorities with room to rest.",
    prompt: "Help me plan a realistic week around three priorities, with time left for rest.",
    icon: Route,
  },
];
