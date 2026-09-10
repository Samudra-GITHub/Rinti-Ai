"use client";

import { motion } from "framer-motion";
import { Check } from "lucide-react";
import { Card } from "@/ui/Card";
import { Button } from "@/ui/Button";
import { cn } from "@/lib/cn";
import type { ModelAvailabilityDto } from "@/lib/api";

interface ModelCardProps {
  model: ModelAvailabilityDto;
  active?: boolean;
  onSelect?: (id: string) => void;
}

export function ModelCard({ model, active = false, onSelect }: ModelCardProps) {
  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
      <Card
        hover
        className={cn("flex h-full flex-col gap-4", active && "border-purple-400/40 shadow-glow-purple")}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="h-9 w-9 rounded-full bg-gradient-to-br from-purple-400 to-cyan-400" />
            <div>
              <h3 className="break-all text-sm font-medium text-white/90">{model.id}</h3>
              <p className="text-xs text-white/40">{model.provider}</p>
            </div>
          </div>
          {active && (
            <span className="flex shrink-0 items-center gap-1 rounded-full border border-purple-400/40 bg-purple-500/15 px-2 py-1 text-[11px] text-purple-200">
              <Check size={12} />
              Active
            </span>
          )}
        </div>

        <div className="mt-auto flex items-center justify-between border-t border-white/5 pt-3">
          <span className="text-[11px] text-white/40">Available</span>
          {onSelect && (
            <Button size="sm" variant={active ? "secondary" : "primary"} onClick={() => onSelect(model.id)}>
              {active ? "Selected" : "Use model"}
            </Button>
          )}
        </div>
      </Card>
    </motion.div>
  );
}
