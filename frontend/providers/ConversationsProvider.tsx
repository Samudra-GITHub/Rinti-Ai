"use client";

import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import { api, type ConversationSummary } from "@/lib/api";

interface ConversationsContextValue {
  conversations: ConversationSummary[];
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export const ConversationsContext = createContext<ConversationsContextValue | null>(null);

export function ConversationsProvider({ children }: { children: React.ReactNode }) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await api.listConversations();
      setConversations(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load conversations");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const value = useMemo(
    () => ({ conversations, isLoading, error, refresh }),
    [conversations, isLoading, error, refresh]
  );

  return <ConversationsContext.Provider value={value}>{children}</ConversationsContext.Provider>;
}
