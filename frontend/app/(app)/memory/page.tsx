"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { MemoryCard } from "@/components/memory/MemoryCard";
import { Card } from "@/ui/Card";
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
      setError(e instanceof Error ? e.message : "Failed to load memory");
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
      setError(e instanceof Error ? e.message : "Failed to add memory");
    } finally {
      setIsCreating(false);
    }
  }

  async function handleSave(id: string, content: string) {
    try {
      await api.updateMemory(id, { content });
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update memory");
    }
  }

  async function handleDelete(id: string) {
    try {
      await api.deleteMemory(id);
      setMemories((prev) => prev.filter((m) => m.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete memory");
      await refresh();
    }
  }

  async function handleToggleEnabled(id: string, enabled: boolean) {
    setMemories((prev) => prev.map((m) => (m.id === id ? { ...m, enabled } : m)));
    try {
      await api.setMemoryEnabled(id, enabled);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update memory");
      await refresh();
    }
  }

  return (
    <div className="mx-auto max-w-6xl py-6">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-white/95">Memory</h1>
        <p className="mt-1 text-sm text-white/45">
          What Rinti remembers about you and your work, stored in the backend.
        </p>
      </div>

      <Card className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          value={newContent}
          onChange={(e) => setNewContent(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          placeholder="Add something for Rinti to remember..."
          className="min-w-0 flex-1 rounded-lg bg-white/5 px-3 py-2 text-sm text-white/90 placeholder:text-white/30 focus:outline-none"
        />
        <input
          value={newCategory}
          onChange={(e) => setNewCategory(e.target.value)}
          placeholder="category"
          className="w-full rounded-lg bg-white/5 px-3 py-2 text-sm text-white/70 placeholder:text-white/30 focus:outline-none sm:w-32"
        />
        <Button size="sm" onClick={handleCreate} disabled={!newContent.trim() || isCreating}>
          <Plus size={14} />
          Add
        </Button>
      </Card>

      {error && (
        <p className="mb-4 rounded-xl border border-red-400/25 bg-red-500/10 px-4 py-2.5 text-sm text-red-200">
          {error}
        </p>
      )}

      {isLoading ? (
        <p className="text-sm text-white/40">Loading memory…</p>
      ) : memories.length === 0 ? (
        <p className="text-sm text-white/40">Nothing saved yet — add something above.</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {memories.map((memory) => (
            <MemoryCard
              key={memory.id}
              memory={memory}
              onSave={handleSave}
              onDelete={handleDelete}
              onToggleEnabled={handleToggleEnabled}
            />
          ))}
        </div>
      )}
    </div>
  );
}
