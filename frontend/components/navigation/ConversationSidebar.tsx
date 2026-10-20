"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import { BrainCircuit, Check, LayoutGrid, PanelLeftClose, Pencil, Plus, Settings, Trash2, X } from "lucide-react";
import { useConversations } from "@/hooks/useConversations";
import { api, ApiError, type ConversationSummary } from "@/lib/api";
import { historyBucket } from "@/lib/time";
import { cn } from "@/lib/cn";
import { RintiOrb } from "@/components/orb/RintiOrb";
import { IconButton } from "@/ui/IconButton";

interface ConversationSidebarProps {
  isOpen: boolean;
  isDesktop: boolean;
  onClose: () => void;
}

const footerLinks = [
  { href: "/memory", label: "Memory", icon: BrainCircuit },
  { href: "/models", label: "Models", icon: LayoutGrid },
  { href: "/settings", label: "Settings", icon: Settings },
];

const BUCKET_ORDER = ["Today", "Yesterday", "Previous 7 days", "Earlier"] as const;

/**
 * Reads the open conversation id from the URL. Isolated in its own component so
 * only this leaf (not the whole sidebar) needs a Suspense boundary for
 * useSearchParams.
 */
function ActiveConversationWatcher({ onChange }: { onChange: (id: string | null) => void }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const id = pathname === "/" || pathname === "/chat" ? searchParams.get("c") : null;
  useEffect(() => {
    onChange(id);
  }, [id, onChange]);
  return null;
}

export function ConversationSidebar({ isOpen, isDesktop, onClose }: ConversationSidebarProps) {
  const pathname = usePathname();
  const { conversations, isLoading, error, refresh } = useConversations();

  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [renameError, setRenameError] = useState<string | null>(null);
  const [savingRenameId, setSavingRenameId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Close the drawer after navigating (small screens only).
  useEffect(() => {
    if (!isDesktop) onClose();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname, activeConversationId]);

  useEffect(() => {
    if (!isOpen || isDesktop) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [isOpen, isDesktop, onClose]);

  const groups = useMemo(() => {
    const buckets = new Map<string, ConversationSummary[]>();
    for (const conversation of conversations) {
      const key = historyBucket(conversation.updated_at ?? conversation.created_at);
      buckets.set(key, [...(buckets.get(key) ?? []), conversation]);
    }
    return BUCKET_ORDER.filter((key) => buckets.has(key)).map((key) => ({ key, items: buckets.get(key)! }));
  }, [conversations]);

  function startRename(id: string, currentTitle: string | null) {
    setConfirmDeleteId(null);
    setRenamingId(id);
    setRenameDraft(currentTitle ?? "");
    setRenameError(null);
  }

  function cancelRename() {
    setRenamingId(null);
    setRenameError(null);
  }

  async function commitRename(id: string) {
    if (savingRenameId) return; // already saving, ignore duplicate submits
    const title = renameDraft.trim();
    if (!title) {
      setRenameError("Title can't be empty");
      return;
    }
    setSavingRenameId(id);
    try {
      await api.renameConversation(id, title);
      setRenamingId(null);
      setRenameError(null);
      await refresh();
    } catch (e) {
      setRenameError(e instanceof ApiError ? e.message : "Couldn't rename. Try again.");
    } finally {
      setSavingRenameId(null);
    }
  }

  async function handleDelete(id: string) {
    if (deletingId) return; // already deleting one, ignore duplicate clicks
    setDeletingId(id);
    try {
      await api.deleteConversation(id);
    } catch {
      // Already gone (404) or a transient error either way: refresh to reconcile.
    }
    await refresh();
    setDeletingId(null);
    setConfirmDeleteId(null);
    if (activeConversationId === id) {
      // Leave the deleted conversation: a full navigation resets the chat screen.
      window.location.assign("/");
    }
  }

  const content = (
    <div className="flex h-full w-72 max-w-[86vw] flex-col lg:max-w-none lg:pr-3">
      <div className="flex items-center justify-between px-4 pb-3 pt-4 pt-safe">
        <Link href="/" className="flex items-center gap-2.5 rounded-lg focus-ring" aria-label="Rinti AI home">
          <RintiOrb size="xs" />
          <span className="font-display text-[1.3rem] font-medium leading-none tracking-[-0.04em] text-fg">Rinti</span>
        </Link>
        <IconButton icon={PanelLeftClose} aria-label="Collapse sidebar" size="sm" appearance="bare" onClick={onClose} />
      </div>

      <div className="px-3">
        <Link
          href="/"
          className="edge-light flex h-10 items-center gap-2.5 rounded-xl border border-fg/10 bg-fg/[0.04] px-3 text-sm font-medium text-fg/85 transition-[background-color,border-color] duration-150 hover:border-fg/20 hover:bg-fg/8 focus-ring"
        >
          <Plus size={16} strokeWidth={1.9} className="text-purple-300" />
          New chat
        </Link>
      </div>

      <nav aria-label="Conversation history" className="mt-4 min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 pb-3">
        {isLoading && <p className="px-2 py-2 text-xs text-fg/35">Loading conversations…</p>}
        {error && !isLoading && (
          <div className="px-2 py-2">
            <p className="text-xs text-red-600 dark:text-red-300/90">{error}</p>
            <button
              onClick={() => refresh()}
              className="mt-1 text-xs text-purple-300 underline-offset-2 hover:underline focus-ring"
            >
              Try again
            </button>
          </div>
        )}
        {!isLoading && !error && conversations.length === 0 && (
          <p className="px-2 py-2 text-xs leading-relaxed text-fg/35">Your conversations will appear here.</p>
        )}

        {groups.map((group) => (
          <section key={group.key} className="mb-4">
            <h2 className="px-2 pb-1.5 text-[11px] font-medium tracking-wide text-fg/35">{group.key}</h2>
            <ul className="space-y-0.5">
              {group.items.map((conversation) => {
                const isRenaming = renamingId === conversation.id;
                const isSaving = savingRenameId === conversation.id;
                const isDeleting = deletingId === conversation.id;
                const isConfirming = confirmDeleteId === conversation.id;
                const isActive = activeConversationId === conversation.id;
                return (
                  <li
                    key={conversation.id}
                    className={cn(
                      "group relative rounded-xl transition-colors duration-150",
                      isActive ? "bg-fg/9" : "hover:bg-fg/5",
                      isDeleting && "opacity-50"
                    )}
                  >
                    {isRenaming ? (
                      <div className="flex flex-col gap-1 p-1.5">
                        <div className="flex items-center gap-1">
                          <input
                            autoFocus
                            value={renameDraft}
                            disabled={isSaving}
                            onChange={(e) => setRenameDraft(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") commitRename(conversation.id);
                              if (e.key === "Escape") cancelRename();
                            }}
                            aria-label="Conversation title"
                            aria-invalid={!!renameError}
                            className="min-w-0 flex-1 rounded-lg bg-fg/10 px-2 py-1.5 text-sm text-fg focus:outline-none focus-visible:ring-2 focus-visible:ring-purple-400/60 disabled:opacity-50"
                          />
                          <IconButton icon={X} size="sm" appearance="bare" aria-label="Cancel rename" onClick={cancelRename} disabled={isSaving} />
                          <IconButton icon={Check} size="sm" appearance="bare" aria-label="Save name" onClick={() => commitRename(conversation.id)} disabled={isSaving} />
                        </div>
                        {renameError && <span className="px-1 text-[11px] text-red-600 dark:text-red-300/90">{renameError}</span>}
                      </div>
                    ) : isConfirming ? (
                      <div className="flex items-center justify-between gap-2 px-3 py-2">
                        <span className="text-sm text-fg/75">Delete this chat?</span>
                        <span className="flex items-center gap-1">
                          <button
                            onClick={() => setConfirmDeleteId(null)}
                            disabled={isDeleting}
                            className="rounded-md px-2 py-1 text-xs text-fg/60 hover:bg-fg/10 hover:text-fg focus-ring"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={() => handleDelete(conversation.id)}
                            disabled={isDeleting}
                            className="rounded-md bg-red-500/15 px-2 py-1 text-xs font-medium text-red-600 hover:bg-red-500/25 focus-ring dark:text-red-300"
                          >
                            {isDeleting ? "Deleting…" : "Delete"}
                          </button>
                        </span>
                      </div>
                    ) : (
                      <>
                        <Link
                          href={`/chat?c=${conversation.id}`}
                          aria-current={isActive ? "page" : undefined}
                          className="block truncate rounded-xl py-2 pl-3 pr-16 text-sm text-fg/75 focus-ring group-hover:text-fg aria-[current=page]:text-fg"
                          title={conversation.title ?? "New conversation"}
                        >
                          {conversation.title ?? "New conversation"}
                        </Link>
                        <span className="absolute right-1 top-1/2 flex -translate-y-1/2 items-center opacity-0 transition-opacity duration-150 focus-within:opacity-100 group-hover:opacity-100 max-lg:opacity-100">
                          <IconButton
                            icon={Pencil}
                            size="sm"
                            appearance="bare"
                            aria-label="Rename conversation"
                            onClick={() => startRename(conversation.id, conversation.title)}
                            className="h-7 w-7"
                          />
                          <IconButton
                            icon={Trash2}
                            size="sm"
                            appearance="bare"
                            aria-label="Delete conversation"
                            onClick={() => setConfirmDeleteId(conversation.id)}
                            className="h-7 w-7 hover:text-red-600 dark:hover:text-red-300"
                          />
                        </span>
                      </>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        ))}
      </nav>

      <div className="border-t border-fg/8 p-3 pb-safe">
        <ul className="space-y-0.5">
          {footerLinks.map((item) => {
            const isActive = pathname === item.href;
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  aria-current={isActive ? "page" : undefined}
                  className={cn(
                    "flex items-center gap-3 rounded-xl px-3 py-2 text-sm transition-colors duration-150 focus-ring",
                    isActive ? "bg-fg/9 text-fg" : "text-fg/55 hover:bg-fg/5 hover:text-fg"
                  )}
                >
                  <item.icon size={16} strokeWidth={1.8} className={isActive ? "text-purple-300" : undefined} />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );

  return (
    <>
      <Suspense fallback={null}>
        <ActiveConversationWatcher onChange={setActiveConversationId} />
      </Suspense>

      {isDesktop ? (
        <motion.aside
          initial={false}
          animate={{ width: isOpen ? 288 : 0 }}
          transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
          className="relative z-20 shrink-0 overflow-hidden"
          aria-hidden={!isOpen}
          // `inert` keeps a collapsed sidebar's links out of the tab order.
          {...(!isOpen ? { inert: true } : {})}
        >
          {content}
        </motion.aside>
      ) : (
        <AnimatePresence>
          {isOpen && (
            <>
              <motion.button
                key="scrim"
                type="button"
                aria-label="Close sidebar"
                onClick={onClose}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.2 }}
                className="fixed inset-0 z-30 bg-black/55 backdrop-blur-[2px]"
              />
              <motion.aside
                key="drawer"
                role="dialog"
                aria-label="Navigation"
                initial={{ x: "-100%" }}
                animate={{ x: 0 }}
                exit={{ x: "-100%" }}
                transition={{ type: "spring", stiffness: 380, damping: 38 }}
                className="fixed inset-y-0 left-0 z-40 w-72 max-w-[86vw] overflow-hidden border-r border-fg/10 bg-surface shadow-2xl"
              >
                {content}
              </motion.aside>
            </>
          )}
        </AnimatePresence>
      )}
    </>
  );
}
