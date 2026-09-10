"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { AnimatePresence, motion } from "framer-motion";
import {
  Compass,
  MessagesSquare,
  BrainCircuit,
  LayoutGrid,
  Settings,
  X,
  Plus,
  Pencil,
  Trash2,
  Check,
  LogOut,
} from "lucide-react";
import { useActiveModel } from "@/hooks/useActiveModel";
import { useConversations } from "@/hooks/useConversations";
import { useAuth } from "@/hooks/useAuth";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/cn";
import { RintiOrb } from "@/components/orb/RintiOrb";
import { IconButton } from "@/ui/IconButton";

interface ConversationSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

const navItems = [
  { href: "/", label: "Overview", icon: Compass },
  { href: "/chat", label: "Chat", icon: MessagesSquare },
  { href: "/memory", label: "Memory", icon: BrainCircuit },
  { href: "/models", label: "Models", icon: LayoutGrid },
  { href: "/settings", label: "Settings", icon: Settings },
];

/**
 * Reads the open conversation id from the URL. Isolated in its own component so
 * only this leaf (not the whole sidebar, not the other statically-rendered
 * routes that mount the sidebar via AppShell) needs a Suspense boundary for
 * useSearchParams.
 */
function ActiveConversationWatcher({ onChange }: { onChange: (id: string | null) => void }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const id = pathname === "/chat" ? searchParams.get("c") : null;
  useEffect(() => {
    onChange(id);
  }, [id, onChange]);
  return null;
}

export function ConversationSidebar({ isOpen, onClose }: ConversationSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  const { activeModel, setActiveModel, availableModels } = useActiveModel();
  const { conversations, isLoading, error, refresh } = useConversations();
  const { user, logout } = useAuth();
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [renameError, setRenameError] = useState<string | null>(null);
  const [savingRenameId, setSavingRenameId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  function startRename(id: string, currentTitle: string | null) {
    setRenamingId(id);
    setRenameDraft(currentTitle ?? "");
    setRenameError(null);
  }

  function cancelRename() {
    setRenamingId(null);
    setRenameError(null);
  }

  async function commitRename(id: string) {
    if (savingRenameId) return; // already saving — ignore duplicate submits
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
      setRenameError(e instanceof ApiError ? e.message : "Couldn't rename — try again");
    } finally {
      setSavingRenameId(null);
    }
  }

  async function handleDelete(id: string) {
    if (deletingId) return; // already deleting one — ignore duplicate clicks
    if (!window.confirm("Delete this conversation? This can't be undone.")) return;
    setDeletingId(id);
    try {
      await api.deleteConversation(id);
    } catch {
      // Already gone (404) or a transient error either way — refresh to reconcile.
    }
    await refresh();
    setDeletingId(null);
    if (activeConversationId === id) {
      router.push("/chat");
    }
  }

  async function handleLogout() {
    if (isLoggingOut) return;
    setIsLoggingOut(true);
    try {
      await logout();
    } finally {
      router.replace("/login");
    }
  }

  return (
    <>
      <Suspense fallback={null}>
        <ActiveConversationWatcher onChange={setActiveConversationId} />
      </Suspense>

      <AnimatePresence>
        {isOpen && (
          <motion.button
            aria-label="Close sidebar"
            onClick={onClose}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-30 bg-black/50 backdrop-blur-sm lg:hidden"
          />
        )}
      </AnimatePresence>

      <AnimatePresence initial={false}>
        {isOpen && (
          <motion.aside
            initial={{ x: -300, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -300, opacity: 0 }}
            transition={{ type: "spring", stiffness: 300, damping: 32 }}
            className="glass-panel fixed inset-y-0 left-0 z-40 flex w-72 flex-col rounded-none border-y-0 border-l-0 px-4 py-5 lg:static lg:z-0 lg:h-screen lg:rounded-none"
          >
            <div className="flex items-center justify-between px-1">
              <Link href="/" className="flex items-center gap-2.5">
                <RintiOrb size="sm" />
                <span className="text-sm font-semibold tracking-wide text-white/90">
                  Rinti AI
                </span>
              </Link>
              <IconButton
                icon={X}
                aria-label="Close sidebar"
                size="sm"
                onClick={onClose}
                className="lg:hidden"
              />
            </div>

            <nav className="mt-6 flex flex-col gap-1">
              {navItems.map((item) => {
                const isActive = pathname === item.href;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={isActive ? "page" : undefined}
                    className={cn(
                      "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors duration-200 focus-ring",
                      isActive
                        ? "bg-white/10 text-white"
                        : "text-white/55 hover:bg-white/5 hover:text-white/90"
                    )}
                  >
                    <item.icon
                      size={16}
                      className={cn(
                        isActive ? "text-purple-300" : "text-white/40 group-hover:text-white/70"
                      )}
                    />
                    {item.label}
                  </Link>
                );
              })}
            </nav>

            <div className="mt-6 border-t border-white/5 pt-4">
              <p className="px-1 text-[11px] font-medium uppercase tracking-wider text-white/35">
                Active model
              </p>
              <div className="mt-2 flex flex-wrap gap-1.5 px-1">
                {availableModels.length === 0 ? (
                  <span className="text-[11px] text-white/30">No model configured</span>
                ) : (
                  availableModels.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => setActiveModel(m.id)}
                      aria-pressed={activeModel === m.id}
                      className={cn(
                        "rounded-full border px-2.5 py-1 text-[11px] transition-all duration-200 focus-ring",
                        activeModel === m.id
                          ? "border-purple-400/50 bg-purple-500/15 text-white"
                          : "border-white/10 bg-white/5 text-white/50 hover:text-white/80"
                      )}
                    >
                      {m.id}
                    </button>
                  ))
                )}
              </div>
            </div>

            <div className="mt-6 flex flex-1 flex-col overflow-hidden border-t border-white/5 pt-4">
              <div className="flex items-center justify-between px-1">
                <p className="text-[11px] font-medium uppercase tracking-wider text-white/35">
                  Conversations
                </p>
                <Link
                  href="/chat"
                  aria-label="Start new conversation"
                  className="flex h-6 w-6 items-center justify-center rounded-full text-white/40 hover:bg-white/10 hover:text-white/80"
                >
                  <Plus size={14} />
                </Link>
              </div>

              <div data-lenis-prevent className="mt-2 flex-1 space-y-1 overflow-y-auto overscroll-contain pr-1">
                {isLoading && (
                  <p className="px-3 py-2 text-xs text-white/30">Loading conversations…</p>
                )}
                {error && !isLoading && (
                  <div className="px-3 py-2">
                    <p className="text-xs text-red-300/80">{error}</p>
                    <button
                      onClick={() => refresh()}
                      className="mt-1 text-xs text-purple-300/80 underline-offset-2 hover:underline focus-ring"
                    >
                      Try again
                    </button>
                  </div>
                )}
                {!isLoading && !error && conversations.length === 0 && (
                  <p className="px-3 py-2 text-xs text-white/30">
                    No conversations yet — start one from Chat.
                  </p>
                )}
                {conversations.map((conversation) => {
                  const isRenaming = renamingId === conversation.id;
                  const isSaving = savingRenameId === conversation.id;
                  const isDeleting = deletingId === conversation.id;
                  const isActive = activeConversationId === conversation.id;
                  return (
                    <div
                      key={conversation.id}
                      aria-current={isActive ? "true" : undefined}
                      className={cn(
                        "group flex items-center gap-1 rounded-xl px-2 py-1.5 transition-colors duration-200",
                        isActive ? "bg-white/10" : "hover:bg-white/5",
                        isDeleting && "opacity-50"
                      )}
                    >
                      {isRenaming ? (
                        <div className="flex flex-1 flex-col gap-1 px-1">
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
                              className="min-w-0 flex-1 rounded-lg bg-white/10 px-2 py-1 text-sm text-white/90 focus:outline-none disabled:opacity-50"
                            />
                            <IconButton
                              icon={X}
                              size="sm"
                              aria-label="Cancel rename"
                              onClick={cancelRename}
                              disabled={isSaving}
                            />
                            <IconButton
                              icon={Check}
                              size="sm"
                              aria-label="Save name"
                              onClick={() => commitRename(conversation.id)}
                              disabled={isSaving}
                            />
                          </div>
                          {renameError && (
                            <span className="px-1 text-[11px] text-red-300/80">{renameError}</span>
                          )}
                        </div>
                      ) : (
                        <>
                          <Link
                            href={`/chat?c=${conversation.id}`}
                            aria-current={isActive ? "page" : undefined}
                            className="flex min-w-0 flex-1 flex-col gap-0.5 rounded-lg px-1 py-1 text-left focus-ring"
                          >
                            <span
                              className={cn(
                                "truncate text-sm",
                                isActive ? "text-white" : "text-white/80"
                              )}
                            >
                              {conversation.title ?? "New conversation"}
                            </span>
                            <span className="text-[11px] text-white/30">
                              {new Date(conversation.updated_at ?? conversation.created_at).toLocaleDateString(
                                undefined,
                                { month: "short", day: "numeric" }
                              )}
                            </span>
                          </Link>
                          <div className="hidden shrink-0 items-center gap-0.5 group-hover:flex">
                            <IconButton
                              icon={Pencil}
                              size="sm"
                              aria-label="Rename conversation"
                              onClick={() => startRename(conversation.id, conversation.title)}
                              disabled={isDeleting}
                            />
                            <IconButton
                              icon={Trash2}
                              size="sm"
                              aria-label="Delete conversation"
                              onClick={() => handleDelete(conversation.id)}
                              disabled={isDeleting}
                            />
                          </div>
                        </>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {user && (
              <div className="mt-4 flex items-center gap-2.5 border-t border-white/5 px-1 pt-4">
                <div
                  aria-hidden
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-purple-400/30 to-cyan-400/30 text-xs font-medium text-white/90"
                >
                  {user.name.trim().charAt(0).toUpperCase() || "?"}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-white/85">{user.name}</p>
                  <p className="truncate text-[11px] text-white/35">{user.email}</p>
                </div>
                <IconButton
                  icon={LogOut}
                  size="sm"
                  aria-label="Log out"
                  onClick={handleLogout}
                  disabled={isLoggingOut}
                />
              </div>
            )}
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  );
}
