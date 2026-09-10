"use client";

import { useContext } from "react";
import { ConversationsContext } from "@/providers/ConversationsProvider";

export function useConversations() {
  const ctx = useContext(ConversationsContext);
  if (!ctx) {
    throw new Error("useConversations must be used within a ConversationsProvider");
  }
  return ctx;
}
