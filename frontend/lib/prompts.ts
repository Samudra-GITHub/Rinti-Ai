export interface PromptSuggestion {
  id: string;
  label: string;
  prompt: string;
}

export const promptSuggestions: PromptSuggestion[] = [
  {
    id: "plan-week",
    label: "Plan my week",
    prompt: "Help me plan a focused, realistic schedule for this week.",
  },
  {
    id: "summarize",
    label: "Summarize a document",
    prompt: "Summarize this document into key takeaways and action items.",
  },
  {
    id: "brainstorm",
    label: "Brainstorm ideas",
    prompt: "Brainstorm ten fresh ideas for a project I'm stuck on.",
  },
  {
    id: "explain-code",
    label: "Explain this code",
    prompt: "Explain what this piece of code does, step by step.",
  },
  {
    id: "draft-email",
    label: "Draft an email",
    prompt: "Draft a clear, polite email about a schedule change.",
  },
  {
    id: "learn-topic",
    label: "Teach me something",
    prompt: "Teach me the basics of a topic I'm curious about, simply.",
  },
];
