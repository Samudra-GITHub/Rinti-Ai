export type MessageRole = "user" | "assistant" | "system";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  researchSessionId?: string | null;
  /** Which model answered (known for replies generated in this session). */
  answeredBy?: { provider: string; model: string; kind: "local" | "cloud" };
}
