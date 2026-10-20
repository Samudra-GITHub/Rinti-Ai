"use client";

import { Check } from "lucide-react";
import { RintiOrb } from "@/components/orb/RintiOrb";
import { Button } from "@/ui/Button";
import { cn } from "@/lib/cn";
import type { ModelAvailabilityDto } from "@/lib/api";

interface ModelCardProps {
  model: ModelAvailabilityDto;
  active?: boolean;
  onSelect?: (id: string) => void;
}

/** One model as a list row: name and provider, with a clear active state. */
export function ModelCard({ model, active = false, onSelect }: ModelCardProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-4 rounded-2xl border px-4 py-3.5 transition-colors duration-150",
        active ? "border-purple-400/35 bg-purple-500/[0.07]" : "border-fg/10 bg-surface/50 hover:border-fg/20"
      )}
    >
      <RintiOrb size="sm" />
      <div className="min-w-0 flex-1">
        <h3 className="truncate text-sm font-medium text-fg/90">{model.id}</h3>
        <p className="text-xs text-fg/40">{model.provider}</p>
      </div>
      {active ? (
        <span className="flex shrink-0 items-center gap-1.5 text-xs font-medium text-purple-300">
          <Check size={14} />
          In use
        </span>
      ) : (
        onSelect && (
          <Button size="sm" variant="secondary" onClick={() => onSelect(model.id)}>
            Use this model
          </Button>
        )
      )}
    </div>
  );
}
