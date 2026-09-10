"use client";

import { useCallback, useEffect, useState } from "react";

export function useSidebar(defaultOpen = true) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  useEffect(() => {
    const mql = window.matchMedia("(max-width: 1024px)");
    if (mql.matches) setIsOpen(false);
  }, []);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  return { isOpen, open, close, toggle };
}
