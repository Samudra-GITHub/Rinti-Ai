"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { api, toMessage } from "@/lib/api";
import type { Message } from "@/types/conversation";

function ThreadSkeleton() {
  return (
    <div className="mx-auto w-full max-w-[44rem] flex-1 space-y-8 px-4 pt-10 sm:px-6" role="status" aria-label="Loading conversation">
      <div className="ml-auto h-10 w-2/5 animate-pulse rounded-2xl bg-fg/[0.06]" />
      <div className="space-y-2.5">
        <div className="h-3.5 w-full animate-pulse rounded bg-fg/[0.06]" />
        <div className="h-3.5 w-[92%] animate-pulse rounded bg-fg/[0.06]" />
        <div className="h-3.5 w-3/5 animate-pulse rounded bg-fg/[0.06]" />
      </div>
    </div>
  );
}

function ChatScreenContent() {
  const searchParams = useSearchParams();
  const conversationId = searchParams.get("c");
  const draft = searchParams.get("draft") ?? "";

  const [messages, setMessages] = useState<Message[] | null>(null); // null = loading
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
      // the loading fallback below, unmounting it and discarding that state
      // for nothing.
      return;
    }

    if (!conversationId) {
      setMessages([]);
      setLoadError(null);
      return;
    }

    setMessages(null);
    setLoadError(null);

    api
      .getConversationMessages(conversationId)
      .then((backendMessages) => {
        if (cancelled) return;
        setMessages(backendMessages.map(toMessage));
      })
      .catch((e) => {
        if (cancelled) return;
        setLoadError(e instanceof Error ? e.message : "Couldn't load this conversation. Check your connection and try again.");
        setMessages([]);
      });

    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  if (messages === null) return <ThreadSkeleton />;

  return (
    <ChatWindow
      conversationId={conversationId}
      initialMessages={messages}
      initialDraft={draft}
      loadError={loadError}
    />
  );
}

/** The one chat interface: the landing hero when empty, the conversation otherwise. */
export function ChatScreen() {
  return (
    <Suspense fallback={null}>
      <ChatScreenContent />
    </Suspense>
  );
}
