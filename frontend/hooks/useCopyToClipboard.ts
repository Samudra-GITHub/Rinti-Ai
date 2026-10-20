"use client";

import { useCallback, useEffect, useRef, useState } from "react";

function legacyCopy(text: string): boolean {
  try {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.cssText = "position:fixed;top:0;left:0;opacity:0;pointer-events:none";
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(area);
    return ok;
  } catch {
    return false;
  }
}

async function writeText(text: string): Promise<boolean> {
  // The async Clipboard API can reject (insecure context, permissions) or even
  // never settle (document not focused), so give it a short deadline and fall
  // back to a hidden textarea + execCommand.
  if (navigator.clipboard?.writeText) {
    const settled = await Promise.race([
      navigator.clipboard.writeText(text).then(
        () => true,
        () => false
      ),
      new Promise<false>((resolve) => setTimeout(() => resolve(false), 1200)),
    ]);
    if (settled) return true;
  }
  return legacyCopy(text);
}

/** Copies text and reports `copied` / `failed` for a short moment, for button feedback. */
export function useCopyToClipboard(resetMs = 1800) {
  const [status, setStatus] = useState<"idle" | "copied" | "failed">("idle");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  const copy = useCallback(
    async (text: string) => {
      const ok = await writeText(text);
      setStatus(ok ? "copied" : "failed");
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setStatus("idle"), resetMs);
      return ok;
    },
    [resetMs]
  );

  return { copy, status };
}
