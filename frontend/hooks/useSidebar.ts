"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "rinti-sidebar";
const DESKTOP_QUERY = "(min-width: 1024px)";

/**
 * Sidebar state. On desktop it is a persistent column whose open/closed choice
 * is remembered; on small screens it is a drawer that always starts closed.
 */
export function useSidebar() {
  const [isDesktop, setIsDesktop] = useState(true);
  const [isOpen, setIsOpen] = useState(true);

  useEffect(() => {
    const media = window.matchMedia(DESKTOP_QUERY);

    function sync() {
      setIsDesktop(media.matches);
      if (!media.matches) {
        setIsOpen(false);
        return;
      }
      let stored: string | null = null;
      try {
        stored = window.localStorage.getItem(STORAGE_KEY);
      } catch {
        // ignore unavailable storage
      }
      setIsOpen(stored !== "closed");
    }

    sync();
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, []);

  const set = useCallback(
    (next: boolean) => {
      setIsOpen(next);
      if (!isDesktop) return;
      try {
        window.localStorage.setItem(STORAGE_KEY, next ? "open" : "closed");
      } catch {
        // ignore unavailable storage
      }
    },
    [isDesktop]
  );

  const toggle = useCallback(() => set(!isOpen), [set, isOpen]);
  const close = useCallback(() => set(false), [set]);

  return { isOpen, isDesktop, toggle, close };
}
