import { Sparkles } from "lucide-react";

export function TypingIndicator() {
  return (
    <div className="flex w-full items-center gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-purple-300/30 bg-purple-500/15 text-purple-200">
        <Sparkles size={15} />
      </div>
      <div className="glass flex items-center gap-1.5 rounded-2xl rounded-tl-sm px-4 py-3.5">
        <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-white/70 [animation-delay:-0.32s]" />
        <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-white/70 [animation-delay:-0.16s]" />
        <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-white/70" />
      </div>
    </div>
  );
}
