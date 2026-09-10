"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Tag, Pencil, Trash2, Check, X } from "lucide-react";
import { Card } from "@/ui/Card";
import { Switch } from "@/ui/Switch";
import type { MemoryItemDto } from "@/lib/api";

interface MemoryCardProps {
  memory: MemoryItemDto;
  onSave: (id: string, content: string) => Promise<void> | void;
  onDelete: (id: string) => Promise<void> | void;
  onToggleEnabled: (id: string, enabled: boolean) => Promise<void> | void;
}

export function MemoryCard({ memory, onSave, onDelete, onToggleEnabled }: MemoryCardProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [draft, setDraft] = useState(memory.content);

  function startEdit() {
    setDraft(memory.content);
    setIsEditing(true);
  }

  async function commitEdit() {
    const trimmed = draft.trim();
    setIsEditing(false);
    if (!trimmed || trimmed === memory.content) return;
    await onSave(memory.id, trimmed);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
    >
      <Card hover className="flex h-full flex-col gap-3">
        <div className="flex items-start justify-between gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-purple-300/25 bg-purple-500/10 px-2.5 py-1 text-[11px] text-purple-200">
            <Tag size={12} />
            {memory.category}
          </span>
          <Switch
            checked={memory.enabled}
            onCheckedChange={(enabled) => onToggleEnabled(memory.id, enabled)}
            label="Toggle memory enabled"
          />
        </div>

        {isEditing ? (
          <div className="flex flex-1 flex-col gap-2">
            <textarea
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              rows={3}
              className="flex-1 resize-none rounded-lg bg-white/5 p-2 text-sm text-white/90 focus:outline-none"
            />
            <div className="flex justify-end gap-1.5">
              <button
                onClick={() => setIsEditing(false)}
                aria-label="Cancel edit"
                className="rounded-full p-1.5 text-white/40 hover:bg-white/10 hover:text-white/80 focus-ring"
              >
                <X size={14} />
              </button>
              <button
                onClick={commitEdit}
                aria-label="Save memory"
                className="rounded-full p-1.5 text-purple-200 hover:bg-purple-500/15 focus-ring"
              >
                <Check size={14} />
              </button>
            </div>
          </div>
        ) : (
          <p className={`flex-1 text-sm leading-relaxed ${memory.enabled ? "text-white/70" : "text-white/35"}`}>
            {memory.content}
          </p>
        )}

        <div className="flex items-center justify-between border-t border-white/5 pt-2">
          <span className="text-[11px] text-white/30">
            {new Date(memory.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
          </span>
          {!isEditing && (
            <div className="flex items-center gap-0.5">
              <button
                onClick={startEdit}
                aria-label="Edit memory"
                className="rounded-full p-1.5 text-white/30 hover:bg-white/10 hover:text-white/70 focus-ring"
              >
                <Pencil size={13} />
              </button>
              <button
                onClick={() => onDelete(memory.id)}
                aria-label="Delete memory"
                className="rounded-full p-1.5 text-white/30 hover:bg-white/10 hover:text-red-300 focus-ring"
              >
                <Trash2 size={13} />
              </button>
            </div>
          )}
        </div>
      </Card>
    </motion.div>
  );
}
