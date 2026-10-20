"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, LayoutGroup, motion } from "framer-motion";
import { AlertCircle, ArrowDown, RotateCcw, X } from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import { Composer, type ComposerHandle } from "./Composer";
import { Hero, SuggestionRow } from "./Hero";
import { RintiOrb } from "@/components/orb/RintiOrb";
import { useActiveModel } from "@/hooks/useActiveModel";
import { useConversations } from "@/hooks/useConversations";
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

// Width of the reading column, shared by the thread and the composer so the
// composer does not change size when it moves from the landing to the dock.
const COLUMN = "mx-auto w-full max-w-[44rem]";

interface ChatWindowProps {
  conversationId: string | null;
  initialMessages: Message[];
  initialDraft?: string;
  loadError?: string | null;
}

function makeId() {
  return Math.random().toString(36).slice(2, 10);
}

interface SubmitOptions {
  /** Re-answer the conversation's last user message instead of sending a new one. */
  regenerate?: boolean;
}

export function ChatWindow({
  conversationId,
  initialMessages,
  initialDraft = "",
  loadError = null,
}: ChatWindowProps) {
  const { activeModel } = useActiveModel();
  const { refresh: refreshConversations } = useConversations();

  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [draft, setDraft] = useState(initialDraft);
  const [isStreaming, setIsStreaming] = useState(false);
  const [hasStreamedContent, setHasStreamedContent] = useState(false);
  const [error, setError] = useState<{ message: string; retryable: boolean } | null>(
    loadError ? { message: loadError, retryable: false } : null
  );
  const [pinnedToBottom, setPinnedToBottom] = useState(true);
  const [canHover, setCanHover] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const stickRef = useRef(true);
  const composerRef = useRef<ComposerHandle>(null);
  const activeConversationIdRef = useRef<string | null>(conversationId);
  const abortRef = useRef<AbortController | null>(null);
  // True for exactly one [conversationId] effect run: the one caused by our
  // own history.replaceState() right after a send completes. Next.js's App
  // Router patches history.replaceState to keep useSearchParams in sync, so
  // the `conversationId` prop still changes even though we bypassed
  // router.replace() — this guard stops that from re-triggering the full
  // reset below, which would wipe the researchAnswer/messages/error
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
    setCanHover(window.matchMedia("(hover: hover) and (pointer: fine)").matches);
  }, []);

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
    setError(loadError ? { message: loadError, retryable: false } : null);
    setResearchSources([]);
    setResearchNotes([]);
    setResearchStage(null);
    setResearchAnswer(null);
    setSuppressedMessageId(null);
    stickRef.current = true;

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
    if (initialDraft) {
      setDraft(initialDraft);
      composerRef.current?.focus();
    }
  }, [initialDraft]);

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  // --- scrolling: follow new content only while the reader is at the bottom ---
  const scrollToBottom = useCallback((behavior: ScrollBehavior = "auto") => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior });
  }, []);

  function handleScroll() {
    const el = scrollRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 96;
    stickRef.current = atBottom;
    setPinnedToBottom(atBottom);
  }

  useEffect(() => {
    if (stickRef.current) scrollToBottom("auto");
  }, [messages, researchAnswer, researchStage, isStreaming, scrollToBottom]);

  async function submit(rawText: string, { regenerate = false }: SubmitOptions = {}) {
    const text = rawText.trim();
    if (!text || isStreaming) return;

    const optimisticUser: Message = {
      id: makeId(),
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => {
      if (!regenerate) return [...prev, optimisticUser];
      // Regenerate: drop the previous reply, keep the question.
      const last = prev[prev.length - 1];
      return last?.role === "assistant" ? prev.slice(0, -1) : prev;
    });
    if (!regenerate) setDraft("");
    setError(null);
    setIsStreaming(true);
    setHasStreamedContent(false);
    setResearchSources([]);
    setResearchNotes([]);
    setResearchStage(null);
    setResearchAnswer(null);
    setSuppressedMessageId(null);
    stickRef.current = true;
    setPinnedToBottom(true);

    const assistantId = makeId();
    let assistantStarted = false;
    let receivedStructuredAnswer = false;
    let receivedError = false;
    const wasNewConversation = !activeConversationIdRef.current;
    // Whether the backend has stored this user turn. If not (offline, rate
    // limit, validation), the text goes back into the composer instead.
    let persisted = false;

    const controller = new AbortController();
    abortRef.current = controller;

    function failBeforePersist(message: string) {
      setError({ message, retryable: false });
      if (!regenerate) {
        setMessages((prev) => prev.filter((m) => m.id !== optimisticUser.id));
        setDraft((current) => current || text);
      }
    }

    try {
      // Route to research either because the user asked for it, or because the
      // question needs fresh external facts (automatic routing, backend-classified).
      let useResearch = researchMode && researchAvailable && !regenerate;
      if (!useResearch && researchAvailable && !regenerate) {
        const intent = await detectIntent(text);
        useResearch = Boolean(intent?.needs_research);
      }

      const res = useResearch
        ? await fetch("/api/research/stream", {
            method: "POST",
            headers: withCsrfHeader({ "Content-Type": "application/json" }),
            body: JSON.stringify({
              query: text,
              conversation_id: activeConversationIdRef.current,
              mode: "QUICK",
            }),
            signal: controller.signal,
          })
        : await fetch("/api/chat/stream", {
            method: "POST",
            headers: withCsrfHeader({ "Content-Type": "application/json" }),
            body: JSON.stringify({
              message: text,
              conversation_id: activeConversationIdRef.current,
              model: activeModel,
              regenerate,
            }),
            signal: controller.signal,
          });

      const conversationIdHeader = res.headers.get("x-conversation-id");
      if (conversationIdHeader) {
        activeConversationIdRef.current = conversationIdHeader;
        persisted = true;
      }

      if (!res.ok) {
        // Non-2xx replies are JSON errors, not SSE — surface the backend's
        // own message (rate limit, bad request, ...) instead of a generic one.
        let detail: string | null = null;
        try {
          const body = await res.json();
          if (typeof body?.detail === "string") detail = body.detail;
        } catch {
          // non-JSON body
        }
        failBeforePersist(
          detail ??
            (res.status >= 500
              ? "Something went wrong on our side. Your message is still in the box. Try sending it again."
              : "Rinti couldn't process that request. Please try again.")
        );
        return;
      }

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
            code?: string;
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
            persisted = true;
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
            const message = payload.message ?? "Something went wrong. Please try again.";
            if (persisted) {
              setError({ message, retryable: true });
            } else {
              failBeforePersist(message);
            }
          }
        }
      }

      if (!assistantStarted && !receivedStructuredAnswer && !receivedError) {
        if (persisted) {
          setError({ message: "Rinti didn't return a response. Try again.", retryable: true });
        } else {
          failBeforePersist("Rinti didn't return a response. Please try again.");
        }
      }

      // Update the URL to the real conversation id (so refresh preserves it) and
      // let the sidebar know a conversation was created/updated.
      if (wasNewConversation && activeConversationIdRef.current && persisted) {
        // A router.replace() here would make the parent ChatScreen see a
        // new `c` search param and re-fetch — while that fetch is in flight it
        // renders a loading fallback INSTEAD of this ChatWindow, unmounting it
        // and discarding all the state the live stream just populated
        // (researchAnswer, sources, any error). This component already holds
        // the correct, current state in memory — it doesn't need a refetch,
        // just the address bar to reflect the real id (for refresh/bookmark).
        // history.replaceState does that without going through Next's router.
        // The current path is kept so "/" stays "/" and "/chat" stays "/chat".
        selfNavigatedRef.current = true;
        window.history.replaceState(
          null,
          "",
          `${window.location.pathname}?c=${activeConversationIdRef.current}`
        );
      }
      refreshConversations();
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        // The user pressed Stop. Whatever had streamed so far stays on screen
        // (and the backend saved it), so this is not an error.
        if (activeConversationIdRef.current) refreshConversations();
      } else if (persisted) {
        setError({ message: "The connection dropped before the reply finished. Try again.", retryable: true });
      } else {
        failBeforePersist("Couldn't reach Rinti. Check your connection. Your message is still in the box.");
      }
    } finally {
      setIsStreaming(false);
      setResearchStage(null);
      abortRef.current = null;
      if (canHover) composerRef.current?.focus();
    }
  }

  function handleStop() {
    abortRef.current?.abort();
  }

  const lastUserMessage = [...messages].reverse().find((m) => m.role === "user");

  function handleRetry() {
    if (lastUserMessage) submit(lastUserMessage.content, { regenerate: true });
  }

  const visibleMessages = messages.filter((message) => message.id !== suppressedMessageId);
  const hasMessages = messages.length > 0;
  const lastMessage = messages[messages.length - 1];
  const showThinking = isStreaming && !hasStreamedContent && !researchStage;
  const regenerateAvailable =
    !isStreaming &&
    !researchAnswer &&
    lastMessage?.role === "assistant" &&
    !lastMessage.researchSessionId &&
    Boolean(lastUserMessage) &&
    Boolean(activeConversationIdRef.current);

  const placeholder = isStreaming
    ? researchStage
      ? "Rinti is researching…"
      : "Rinti is replying… you can type your next message"
    : researchMode
      ? "Ask something to research…"
      : hasMessages
        ? "Message Rinti…"
        : "Ask Rinti anything…";

  const composerFooter = researchAvailable ? (
    <>
      <ResearchModeToggle
        enabled={researchMode}
        onToggle={setResearchMode}
        available={researchAvailable}
        disabled={isStreaming}
      />
      <span className="text-[11px] text-fg/35">
        {researchMode
          ? "Searches the web, takes longer, and cites sources"
          : "Rinti searches the web on its own when a question needs it"}
      </span>
    </>
  ) : undefined;

  return (
    <div className={`relative flex h-full min-h-0 flex-col ${hasMessages ? "" : "justify-center"}`}>
      <LayoutGroup>
        <AnimatePresence initial={false} mode="popLayout">
          {!hasMessages && <Hero key="hero" />}
        </AnimatePresence>

        {hasMessages && (
          <div className="relative min-h-0 flex-1">
            <div ref={scrollRef} onScroll={handleScroll} className="h-full overflow-y-auto overscroll-contain">
              <div className={`${COLUMN} px-4 pb-10 pt-4 sm:px-6`}>
                <div className="flex flex-col gap-7">
                  {visibleMessages.map((message, index) => {
                    const isLastVisible = index === visibleMessages.length - 1;
                    const isLiveAssistant = isStreaming && message.id === lastMessage?.id && message.role === "assistant";
                    return (
                      <ChatMessage
                        key={message.id}
                        message={message}
                        isStreaming={isLiveAssistant}
                        canRegenerate={regenerateAvailable && isLastVisible && message.role === "assistant"}
                        onRegenerate={() => lastUserMessage && submit(lastUserMessage.content, { regenerate: true })}
                      />
                    );
                  })}

                  {researchStage && (
                    <ResearchProgress stage={researchStage} label={researchLabel} sourceCount={researchSources.length} />
                  )}
                  {showThinking && (
                    <div className="flex items-center gap-3.5" role="status" aria-live="polite">
                      <RintiOrb size="xs" active />
                      <span className="text-sm text-fg/45">Thinking…</span>
                    </div>
                  )}
                  {researchAnswer && <ResearchAnswerRenderer answer={researchAnswer} />}
                  {researchSources.length > 0 && <SourcesPanel sources={researchSources} notes={researchNotes} />}
                </div>
              </div>
            </div>

            <AnimatePresence>
              {!pinnedToBottom && (
                <motion.button
                  type="button"
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 6 }}
                  transition={{ duration: 0.15 }}
                  onClick={() => {
                    stickRef.current = true;
                    scrollToBottom("smooth");
                  }}
                  aria-label="Scroll to latest message"
                  className="absolute bottom-3 left-1/2 flex h-9 w-9 -translate-x-1/2 items-center justify-center rounded-full border border-fg/12 bg-surface/90 text-fg/70 shadow-composer backdrop-blur hover:text-fg focus-ring"
                >
                  <ArrowDown size={16} />
                </motion.button>
              )}
            </AnimatePresence>
          </div>
        )}

        <motion.div
          layout="position"
          key="composer"
          transition={{ type: "spring", stiffness: 260, damping: 32 }}
          className={hasMessages ? "px-4 pb-4 pt-1 pb-safe sm:px-6" : "px-4 sm:px-6"}
        >
          <div className={COLUMN}>
            <AnimatePresence initial={false}>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 6 }}
                  transition={{ duration: 0.18 }}
                  role="alert"
                  className="mb-3 flex items-start justify-between gap-3 rounded-2xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-200"
                >
                  <span className="flex min-w-0 items-start gap-2.5">
                    <AlertCircle size={15} className="mt-0.5 shrink-0" />
                    <span className="min-w-0 break-words">{error.message}</span>
                  </span>
                  <span className="flex shrink-0 items-center gap-1">
                    {error.retryable && (
                      <button
                        type="button"
                        onClick={handleRetry}
                        className="flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium hover:bg-red-500/15 focus-ring"
                      >
                        <RotateCcw size={12} />
                        Retry
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => setError(null)}
                      aria-label="Dismiss error"
                      className="rounded-full p-1 opacity-70 hover:bg-red-500/15 hover:opacity-100 focus-ring"
                    >
                      <X size={13} />
                    </button>
                  </span>
                </motion.div>
              )}
            </AnimatePresence>

            <Composer
              ref={composerRef}
              value={draft}
              onChange={setDraft}
              onSubmit={() => submit(draft)}
              onStop={handleStop}
              isStreaming={isStreaming}
              placeholder={placeholder}
              autoFocus={canHover && !hasMessages}
              footer={composerFooter}
              size={hasMessages ? "dock" : "hero"}
            />
          </div>
        </motion.div>

        <AnimatePresence initial={false} mode="popLayout">
          {!hasMessages && (
            <SuggestionRow
              key="suggestions"
              onSelect={(prompt) => {
                setDraft(prompt);
                composerRef.current?.focus();
              }}
            />
          )}
        </AnimatePresence>
      </LayoutGroup>
    </div>
  );
}
