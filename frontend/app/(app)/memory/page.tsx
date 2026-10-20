"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { MemoryCard } from "@/components/memory/MemoryCard";
import { PageShell } from "@/components/layout/PageShell";
import { Button } from "@/ui/Button";
import { api, type MemoryItemDto } from "@/lib/api";

export default function MemoryPage() {
  const [memories, setMemories] = useState<MemoryItemDto[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newContent, setNewContent] = useState("");
  const [newCategory, setNewCategory] = useState("general");
  const [isCreating, setIsCreating] = useState(false);

  async function refresh() {
    try {
      const data = await api.listMemory();
      setMemories(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't load your memories.");
    } finally {
      setIsLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreate() {
    const content = newContent.trim();
    if (!content || isCreating) return;
    setIsCreating(true);
    try {
      await api.createMemory(content, newCategory.trim() || "general");
      setNewContent("");
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't save that memory. Try again.");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleSave(id: string, content: string) {
    try {
      await api.updateMemory(id, { content });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't update that memory. Try again.");
    }
  }

  async function handleDelete(id: string) {
    try {
      await api.deleteMemory(id);
      setMemories((prev) => prev.filter((m) => m.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't delete that memory. Try again.");
      await refresh();
    }
  }

  async function handleToggleEnabled(id: string, enabled: boolean) {
    setMemories((prev) => prev.map((m) => (m.id === id ? { ...m, enabled } : m)));
    try {
      await api.setMemoryEnabled(id, enabled);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Couldn't update that memory. Try again.");
      await refresh();
    }
  }

  return (
    <PageShell
      title="Memory"
      description="Facts Rinti can draw on to answer you better. Switch one off to stop using it without deleting it."
    >
      <form
        onSubmit={(e) => {
          e.preventDefault();
          handleCreate();
        }}
        className="flex flex-col gap-2 sm:flex-row"
      >
        <input
          value={newContent}
          onChange={(e) => setNewContent(e.target.value)}
          placeholder="Add something for Rinti to remember…"
          aria-label="New memory"
          className="h-11 min-w-0 rounded-full sm:flex-1 border border-fg/12 bg-fg/[0.04] px-4 text-sm text-fg placeholder:text-fg/35 focus:border-purple-400/45 focus:outline-none"
        />
        <input
          value={newCategory}
          onChange={(e) => setNewCategory(e.target.value)}
          placeholder="Category"
          aria-label="Category"
          className="h-11 w-full rounded-full border border-fg/12 bg-fg/[0.04] px-4 text-sm text-fg/80 placeholder:text-fg/35 focus:border-purple-400/45 focus:outline-none sm:w-36"
        />
        <Button type="submit" size="md" disabled={!newContent.trim() || isCreating}>
          <Plus size={15} />
          Add
        </Button>
      </form>

      {error && (
        <p
          role="alert"
          className="mt-5 rounded-2xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-200"
        >
          {error}
        </p>
      )}

      <div className="mt-8">
        {isLoading ? (
          <div className="space-y-4" role="status" aria-label="Loading memories">
            <div className="h-5 w-3/4 animate-pulse rounded bg-fg/[0.06]" />
            <div className="h-5 w-1/2 animate-pulse rounded bg-fg/[0.06]" />
          </div>
        ) : memories.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-fg/12 px-5 py-10 text-center">
            <p className="text-sm text-fg/70">Nothing saved yet.</p>
            <p className="mt-1 text-[13px] text-fg/40">
              Add a fact above, like how you like answers written or what you&apos;re working on.
            </p>
          </div>
        ) : (
          <ul>
            {memories.map((memory) => (
              <MemoryCard
                key={memory.id}
                memory={memory}
                onSave={handleSave}
                onDelete={handleDelete}
                onToggleEnabled={handleToggleEnabled}
              />
            ))}
          </ul>
        )}
      </div>
    </PageShell>
  );
}
