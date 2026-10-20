"use client";

import { useState } from "react";
import { Check, Pencil, Trash2, X } from "lucide-react";
import { Switch } from "@/ui/Switch";
import { IconButton } from "@/ui/IconButton";
import { cn } from "@/lib/cn";
import { parseTimestamp } from "@/lib/time";
import type { MemoryItemDto } from "@/lib/api";

interface MemoryCardProps {
  memory: MemoryItemDto;
  onSave: (id: string, content: string) => Promise<void> | void;
  onDelete: (id: string) => Promise<void> | void;
  onToggleEnabled: (id: string, enabled: boolean) => Promise<void> | void;
}

/** One remembered fact as a list row, editable in place. */
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
    <li className="group flex items-start gap-3 border-b border-fg/8 px-1 py-4 last:border-b-0">
      <div className="min-w-0 flex-1">
        {isEditing ? (
          <div className="flex flex-col gap-2">
            <textarea
              autoFocus
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Escape") setIsEditing(false);
                if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) commitEdit();
              }}
              rows={3}
              aria-label="Edit memory"
              className="w-full resize-none rounded-xl border border-fg/12 bg-fg/[0.04] p-3 text-sm leading-relaxed text-fg focus:border-purple-400/45 focus:outline-none"
            />
            <div className="flex justify-end gap-1.5">
              <IconButton icon={X} size="sm" aria-label="Cancel edit" onClick={() => setIsEditing(false)} />
              <IconButton icon={Check} size="sm" aria-label="Save memory" active onClick={commitEdit} />
            </div>
          </div>
        ) : (
          <p className={cn("text-sm leading-relaxed", memory.enabled ? "text-fg/85" : "text-fg/35 line-through decoration-fg/20")}>
            {memory.content}
          </p>
        )}
        <p className="mt-1.5 text-xs text-fg/35">
          {memory.category} · {parseTimestamp(memory.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
        </p>
      </div>

      {!isEditing && (
        <div className="flex shrink-0 items-center gap-1 pt-0.5">
          <span className="flex items-center opacity-0 transition-opacity duration-150 focus-within:opacity-100 group-hover:opacity-100 max-lg:opacity-100">
            <IconButton icon={Pencil} size="sm" appearance="bare" aria-label="Edit memory" onClick={startEdit} />
            <IconButton
              icon={Trash2}
              size="sm"
              appearance="bare"
              aria-label="Delete memory"
              onClick={() => onDelete(memory.id)}
              className="hover:text-red-600 dark:hover:text-red-300"
            />
          </span>
          <Switch
            checked={memory.enabled}
            onCheckedChange={(enabled) => onToggleEnabled(memory.id, enabled)}
            label={memory.enabled ? "Stop using this memory" : "Use this memory"}
          />
        </div>
      )}
    </li>
  );
}
