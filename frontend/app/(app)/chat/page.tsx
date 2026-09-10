"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { api, toMessage, type ConversationSummary } from "@/lib/api";
import type { Message } from "@/types/conversation";

function ChatPageContent() {
  const searchParams = useSearchParams();
  const conversationId = searchParams.get("c");
  const draft = searchParams.get("draft") ?? "";

  const [messages, setMessages] = useState<Message[] | null>(null); // null = loading
  const [summary, setSummary] = useState<ConversationSummary | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  // "init" (not null) so the very first render — including a direct visit to
  // /chat?c=existingId — never matches the null->id skip case below.
  const prevConversationIdRef = useRef<string | null | "init">("init");

  useEffect(() => {
    let cancelled = false;
    const previousConversationId = prevConversationIdRef.current;
    prevConversationIdRef.current = conversationId;

    if (previousConversationId === null && conversationId !== null) {
      // The URL just gained a `c` param because ChatWindow's own live send
      // finished and synced the address bar (history.replaceState) — not
      // because the user navigated. ChatWindow already has the right
      // messages/research state in memory; refetching here would swap in
      // the "Loading conversation…" fallback below, unmounting it and
      // discarding that state for nothing.
      return;
    }

    if (!conversationId) {
      setMessages([]);
      setSummary(null);
      setLoadError(null);
      return;
    }

    setMessages(null);
    setLoadError(null);

    Promise.all([api.getConversationMessages(conversationId), api.listConversations()])
      .then(([backendMessages, allConversations]) => {
        if (cancelled) return;
        setMessages(backendMessages.map(toMessage));
        setSummary(allConversations.find((c) => c.id === conversationId) ?? null);
      })
      .catch((e) => {
        if (cancelled) return;
        setLoadError(e instanceof Error ? e.message : "Failed to load this conversation");
        setMessages([]);
      });

    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  return (
    <div className="glass-panel -mx-6 flex h-[calc(100vh-6rem)] flex-col overflow-hidden rounded-xl2 lg:-mx-8">
      {messages === null ? (
        <div className="flex h-full items-center justify-center text-sm text-white/40">
          Loading conversation…
        </div>
      ) : (
        <ChatWindow
          conversationId={conversationId}
          title={summary?.title ?? null}
          initialMessages={messages}
          initialDraft={draft}
          loadError={loadError}
        />
      )}
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense fallback={null}>
      <ChatPageContent />
    </Suspense>
  );
}
