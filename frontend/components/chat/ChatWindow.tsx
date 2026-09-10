"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { AnimatePresence } from "framer-motion";
import { AlertCircle, ArrowUp, Sparkles, X } from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import { TypingIndicator } from "./TypingIndicator";
import { PromptSuggestions } from "./PromptSuggestions";
import { RintiOrb } from "@/components/orb/RintiOrb";
import { IconButton } from "@/ui/IconButton";
import { useActiveModel } from "@/hooks/useActiveModel";
import { useConversations } from "@/hooks/useConversations";
import { useAuth } from "@/hooks/useAuth";
import { extractSseEvents } from "@/lib/sse";
import { withCsrfHeader } from "@/lib/http";
import {
  detectIntent,
  fetchResearchSession,
  fetchResearchStatus,
  type AnswerSectionDto,
  type ResearchAnswerDto,
  type ResearchSourceDto,
  type ResearchStage,
} from "@/lib/research";
import { ResearchModeToggle } from "@/components/research/ResearchModeToggle";
import { ResearchProgress } from "@/components/research/ResearchProgress";
import { SourcesPanel } from "@/components/research/SourcesPanel";
import { ResearchAnswerRenderer } from "@/components/research/ResearchAnswerRenderer";
import type { Message } from "@/types/conversation";

const EMPTY_ANSWER: ResearchAnswerDto = { title: "", query: "", overview: "", executive_summary: [], sections: [] };

interface ChatWindowProps {
  conversationId: string | null;
  title: string | null;
  initialMessages: Message[];
  initialDraft?: string;
  loadError?: string | null;
}

function makeId() {
  return Math.random().toString(36).slice(2, 10);
}

export function ChatWindow({
  conversationId,
  title,
  initialMessages,
  initialDraft = "",
  loadError = null,
}: ChatWindowProps) {
  const router = useRouter();
  const { activeModel } = useActiveModel();
  const { conversations, refresh: refreshConversations } = useConversations();
  const { clearSession } = useAuth();

  // Prefer the live title from the shared conversations list (kept fresh by
  // ConversationsProvider) so a rename made in the sidebar shows up here
  // immediately, without needing a full page reload.
  const liveTitle = conversations.find((c) => c.id === conversationId)?.title ?? title;

  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [draft, setDraft] = useState(initialDraft);
  const [isStreaming, setIsStreaming] = useState(false);
  const [hasStreamedContent, setHasStreamedContent] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(loadError);
  const scrollRef = useRef<HTMLDivElement>(null);
  const activeConversationIdRef = useRef<string | null>(conversationId);
  const abortRef = useRef<AbortController | null>(null);
  // True for exactly one [conversationId] effect run: the one caused by our
  // own history.replaceState() right after a send completes. Next.js's App
  // Router patches history.replaceState to keep useSearchParams in sync, so
  // the `conversationId` prop still changes even though we bypassed
  // router.replace() — this guard stops that from re-triggering the full
  // reset below, which would wipe the researchAnswer/messages/errorMessage
  // the live stream just finished setting.
  const selfNavigatedRef = useRef(false);

  // --- research state ---
  const [researchMode, setResearchMode] = useState(false);
  const [researchAvailable, setResearchAvailable] = useState(false);
  const [researchStage, setResearchStage] = useState<ResearchStage | null>(null);
  const [researchLabel, setResearchLabel] = useState<string | undefined>(undefined);
  const [researchSources, setResearchSources] = useState<ResearchSourceDto[]>([]);
  const [researchNotes, setResearchNotes] = useState<string[]>([]);
  const [researchAnswer, setResearchAnswer] = useState<ResearchAnswerDto | null>(null);
  // Id of a history message whose plain text is superseded by researchAnswer
  // above (the rehydrated structured render replaces its bubble entirely).
  const [suppressedMessageId, setSuppressedMessageId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchResearchStatus()
      .then((status) => {
        if (!cancelled) setResearchAvailable(status.available);
      })
      .catch(() => {
        if (!cancelled) setResearchAvailable(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    activeConversationIdRef.current = conversationId;

    if (selfNavigatedRef.current) {
      selfNavigatedRef.current = false;
      return;
    }

    setMessages(initialMessages);
    setErrorMessage(loadError);
    setResearchSources([]);
    setResearchNotes([]);
    setResearchStage(null);
    setResearchAnswer(null);
    setSuppressedMessageId(null);

    // Rehydrate the sources panel + structured answer for the most recent
    // research turn in this conversation, so refresh renders identically to
    // the live stream (R1.6B §21) instead of falling back to that message's
    // flattened plain-text bubble.
    const lastResearchMessage = [...initialMessages]
      .reverse()
      .find((m) => m.role === "assistant" && m.researchSessionId);
    if (lastResearchMessage?.researchSessionId) {
      let cancelled = false;
      fetchResearchSession(lastResearchMessage.researchSessionId).then((session) => {
        if (cancelled || !session) return;
        setResearchSources(session.result.sources ?? []);
        setResearchNotes(session.result.notes ?? []);
        if (session.result.structured_answer) {
          setResearchAnswer(session.result.structured_answer);
          setSuppressedMessageId(lastResearchMessage.id);
        }
      });
      return () => {
        cancelled = true;
      };
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  useEffect(() => {
    if (initialDraft) setDraft(initialDraft);
  }, [initialDraft]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isStreaming]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  async function handleSend() {
    const text = draft.trim();
    if (!text || isStreaming) return;

    const userMessage: Message = {
      id: makeId(),
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMessage]);
    setDraft("");
    setErrorMessage(null);
    setIsStreaming(true);
    setHasStreamedContent(false);
    setResearchSources([]);
    setResearchNotes([]);
    setResearchStage(null);
    setResearchAnswer(null);
    setSuppressedMessageId(null);

    const assistantId = makeId();
    let assistantStarted = false;
    let receivedStructuredAnswer = false;
    let receivedError = false;
    const wasNewConversation = !activeConversationIdRef.current;

    const controller = new AbortController();
    abortRef.current = controller;

    // Route to research either because the user asked for it, or because the
    // question needs fresh external facts (automatic routing, backend-classified).
    let useResearch = researchMode && researchAvailable;
    if (!useResearch && researchAvailable) {
      const intent = await detectIntent(text);
      useResearch = Boolean(intent?.needs_research);
    }

    try {
      const res = useResearch
        ? await fetch("/api/research", {
            method: "POST",
            headers: withCsrfHeader({ "Content-Type": "application/json" }),
            body: JSON.stringify({
              query: text,
              conversation_id: activeConversationIdRef.current,
              mode: "QUICK",
            }),
            signal: controller.signal,
          })
        : await fetch("/api/chat", {
            method: "POST",
            headers: withCsrfHeader({ "Content-Type": "application/json" }),
            body: JSON.stringify({
              message: text,
              conversation_id: activeConversationIdRef.current,
            }),
            signal: controller.signal,
          });

      const conversationIdHeader = res.headers.get("x-conversation-id");
      if (conversationIdHeader) activeConversationIdRef.current = conversationIdHeader;

      if (!res.body) throw new Error("empty_body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const { events, rest } = extractSseEvents(buffer);
        buffer = rest;

        for (const evt of events) {
          let payload: {
            delta?: string;
            conversationId?: string;
            message?: string;
            stage?: ResearchStage;
            label?: string;
            notes?: string[];
            n?: number;
            title?: string;
            overview?: string;
            executive_summary?: string[];
          } & Partial<ResearchSourceDto> &
            Partial<AnswerSectionDto>;
          try {
            payload = JSON.parse(evt.data);
          } catch {
            continue;
          }

          if (evt.event === "research_status") {
            if (payload.stage) setResearchStage(payload.stage);
            setResearchLabel(payload.label);
          } else if (evt.event === "source") {
            const source = payload as ResearchSourceDto;
            setResearchSources((prev) =>
              prev.some((s) => s.id === source.id) ? prev : [...prev, source]
            );
          } else if (evt.event === "answer_meta") {
            receivedStructuredAnswer = true;
            setHasStreamedContent(true);
            setResearchAnswer((prev) => ({
              ...(prev ?? EMPTY_ANSWER),
              title: payload.title ?? "",
              overview: payload.overview ?? "",
              executive_summary: payload.executive_summary ?? [],
            }));
          } else if (evt.event === "answer_section") {
            receivedStructuredAnswer = true;
            const section = payload as AnswerSectionDto;
            setResearchAnswer((prev) => ({
              ...(prev ?? EMPTY_ANSWER),
              sections: [...(prev?.sections ?? []), section],
            }));
          } else if ((evt.event === "token" || evt.event === "answer_token") && payload.delta) {
            if (!assistantStarted) {
              assistantStarted = true;
              setHasStreamedContent(true);
              setMessages((prev) => [
                ...prev,
                { id: assistantId, role: "assistant", content: "", timestamp: new Date().toISOString() },
              ]);
            }
            const delta = payload.delta;
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + delta } : m))
            );
          } else if (evt.event === "done") {
            if (payload.conversationId) activeConversationIdRef.current = payload.conversationId;
            if (payload.notes?.length) setResearchNotes(payload.notes);
            setResearchStage(null);
          } else if (evt.event === "error") {
            receivedError = true;
            const code = (payload as { code?: string }).code;
            if (code === "unauthenticated") {
              clearSession();
              router.replace("/login");
              return;
            }
            setErrorMessage(payload.message ?? "Something went wrong. Please try again.");
          }
        }
      }

      if (!assistantStarted && !receivedStructuredAnswer && !receivedError) {
        setErrorMessage("Rinti didn't return a response. Please try again.");
      }

      // Update the URL to the real conversation id (so refresh preserves it) and
      // let the sidebar know a conversation was created/updated.
      if (wasNewConversation && activeConversationIdRef.current) {
        // A router.replace() here would make the parent ChatPageContent see a
        // new `c` search param and re-fetch — while that fetch is in flight it
        // renders a loading fallback INSTEAD of this ChatWindow, unmounting it
        // and discarding all the state the live stream just populated
        // (researchAnswer, sources, any error). This component already holds
        // the correct, current state in memory — it doesn't need a refetch,
        // just the address bar to reflect the real id (for refresh/bookmark).
        // history.replaceState does that without going through Next's router.
        selfNavigatedRef.current = true;
        window.history.replaceState(null, "", `/chat?c=${activeConversationIdRef.current}`);
      }
      refreshConversations();
    } catch (err) {
      if ((err as Error).name !== "AbortError") {
        setErrorMessage("Couldn't reach Rinti. Check your connection and try again.");
      }
    } finally {
      setIsStreaming(false);
      setResearchStage(null);
      abortRef.current = null;
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const hasMessages = messages.length > 0;
  const showTypingIndicator = isStreaming && !hasStreamedContent;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-white/5 px-6 py-4">
        <div>
          <h1 className="text-sm font-medium text-white/90">{liveTitle ?? "New conversation"}</h1>
          <p className="text-xs text-white/40">Connected to Rinti&apos;s backend</p>
        </div>
        {activeModel && (
          <span className="glass-inset flex items-center gap-1.5 rounded-full px-3 py-1 text-xs text-white/70">
            <span className="h-1.5 w-1.5 rounded-full bg-gradient-to-r from-purple-400 to-cyan-400" />
            {activeModel}
          </span>
        )}
      </div>

      <div
        ref={scrollRef}
        data-lenis-prevent
        className="flex-1 overflow-y-auto overscroll-contain px-6 py-6"
      >
        {hasMessages ? (
          <div className="mx-auto flex max-w-2xl flex-col gap-5">
            <AnimatePresence initial={false}>
              {messages
                .filter((message) => message.id !== suppressedMessageId)
                .map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}
            </AnimatePresence>
            {researchStage && (
              <ResearchProgress
                stage={researchStage}
                label={researchLabel}
                sourceCount={researchSources.length}
              />
            )}
            {showTypingIndicator && !researchStage && <TypingIndicator />}
            {researchAnswer && <ResearchAnswerRenderer answer={researchAnswer} />}
            {researchSources.length > 0 && (
              <SourcesPanel sources={researchSources} notes={researchNotes} />
            )}
          </div>
        ) : (
          <div className="mx-auto flex h-full max-w-lg flex-col items-center justify-center gap-6 text-center">
            <RintiOrb size="md" active={isStreaming} />
            <div>
              <h2 className="text-lg font-medium text-white/90">How can I help today?</h2>
              <p className="mt-1 text-sm text-white/45">
                Ask anything, or start from a suggestion below.
              </p>
            </div>
            <PromptSuggestions onSelect={setDraft} />
          </div>
        )}
      </div>

      {errorMessage && (
        <div className="mx-6 mb-3 flex items-center justify-between gap-3 rounded-xl border border-red-400/25 bg-red-500/10 px-4 py-2.5 text-sm text-red-200">
          <span className="flex items-center gap-2">
            <AlertCircle size={14} className="shrink-0" />
            {errorMessage}
          </span>
          <button
            onClick={() => setErrorMessage(null)}
            aria-label="Dismiss error"
            className="rounded-full p-1 text-red-200/70 hover:bg-white/10 hover:text-red-100 focus-ring"
          >
            <X size={13} />
          </button>
        </div>
      )}

      <div className="border-t border-white/5 px-6 py-4">
        <div className="glass-panel mx-auto flex max-w-2xl flex-col gap-2 rounded-2xl p-3">
          <div className="flex items-end gap-3">
            <Sparkles size={18} className="mb-2 shrink-0 text-purple-300/70" />
            <textarea
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
              disabled={isStreaming}
              placeholder={
                isStreaming
                  ? researchStage
                    ? "Rinti is researching..."
                    : "Rinti is responding..."
                  : researchMode
                    ? "Ask something to research..."
                    : "Message Rinti..."
              }
              className="max-h-40 min-h-[24px] flex-1 resize-none bg-transparent py-1 text-sm text-white/90 placeholder:text-white/30 focus:outline-none disabled:opacity-50"
            />
            <IconButton
              icon={ArrowUp}
              aria-label="Send message"
              onClick={handleSend}
              disabled={!draft.trim() || isStreaming}
              className="mb-0 bg-gradient-to-r from-purple-500 to-cyan-500 text-white disabled:from-white/10 disabled:to-white/10 disabled:text-white/30"
            />
          </div>

          <div className="flex items-center gap-2 pl-8">
            <ResearchModeToggle
              enabled={researchMode}
              onToggle={setResearchMode}
              available={researchAvailable}
              disabled={isStreaming}
            />
            <span className="text-[11px] text-white/30">
              {!researchAvailable
                ? "Web research unavailable"
                : researchMode
                  ? "Searching the web · takes longer · answers are cited"
                  : "Rinti searches the web automatically when a question needs it"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
