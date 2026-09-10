// Thin client for the FastAPI backend, always called same-origin through this
// app's own /api/* routes (app/api/[...path]/route.ts proxies to FastAPI and
// carries the session cookie both ways — a request straight to the backend's
// own origin would never carry an HttpOnly cookie scoped to this app). SQLite
// (via the backend) is the only source of truth for conversations and memory
// — nothing here caches to localStorage. Non-streaming JSON endpoints only;
// chat/research streaming go through their own SSE proxies instead.
import type { Message } from "@/types/conversation";
import { withCsrfHeader } from "@/lib/http";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export interface ConversationSummary {
  id: string;
  title: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface BackendMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  research_session_id?: string | null;
}

export interface MemoryItemDto {
  id: string;
  content: string;
  category: string;
  enabled: boolean;
  created_at: string;
}

export interface ModelAvailabilityDto {
  id: string;
  provider: string;
  available: boolean;
}

const MUTATING_METHODS = new Set(["POST", "PATCH", "DELETE", "PUT"]);

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? "GET").toUpperCase();
  let res: Response;
  try {
    res = await fetch(path, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(MUTATING_METHODS.has(method) ? withCsrfHeader() : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError(0, "Can't reach Rinti's backend. Is it running?");
  }

  if (res.status === 401) {
    throw new ApiError(401, "Your session has expired. Please log in again.");
  }

  if (!res.ok) {
    // 4xx details from this backend are short, curated, human-written strings
    // ("Title cannot be empty", "Conversation not found") — safe to show as-is.
    // 5xx bodies can carry a raw Python exception string (str(e)) which could
    // include internal detail; never surface that to the browser.
    if (res.status >= 500) {
      throw new ApiError(res.status, "Something went wrong on the server. Please try again.");
    }
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function toMessage(m: BackendMessage): Message {
  return {
    id: m.id,
    role: m.role,
    content: m.content,
    timestamp: m.timestamp,
    researchSessionId: m.research_session_id ?? null,
  };
}

export const api = {
  listConversations: () => request<ConversationSummary[]>("/api/conversations"),
  getConversationMessages: (id: string) => request<BackendMessage[]>(`/api/conversations/${id}`),
  renameConversation: (id: string, title: string) =>
    request<ConversationSummary>(`/api/conversations/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  deleteConversation: (id: string) =>
    request<{ status: string; id: string }>(`/api/conversations/${id}`, { method: "DELETE" }),

  listMemory: () => request<MemoryItemDto[]>("/api/memory"),
  createMemory: (content: string, category = "general") =>
    request<MemoryItemDto>("/api/memory", {
      method: "POST",
      body: JSON.stringify({ content, category }),
    }),
  updateMemory: (id: string, patch: { content?: string; category?: string }) =>
    request<MemoryItemDto>(`/api/memory/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  setMemoryEnabled: (id: string, enabled: boolean) =>
    request<MemoryItemDto>(`/api/memory/${id}/enabled`, {
      method: "PATCH",
      body: JSON.stringify({ enabled }),
    }),
  deleteMemory: (id: string) =>
    request<{ status: string; id: string }>(`/api/memory/${id}`, { method: "DELETE" }),

  listModels: () => request<ModelAvailabilityDto[]>("/api/models"),
};
