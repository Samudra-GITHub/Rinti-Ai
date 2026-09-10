"use client";

import { useEffect, useRef } from "react";
import Lenis from "lenis";

export function useLenisScroll() {
  const lenisRef = useRef<Lenis | null>(null);

  useEffect(() => {
    const lenis = new Lenis({
      duration: 1.1,
      easing: (t: number) => 1 - Math.pow(1 - t, 3),
      smoothWheel: true,
      // Let elements with their own overflow-y-auto (chat messages, sidebar list)
      // scroll natively instead of Lenis hijacking the wheel event for the page.
      allowNestedScroll: true,
    });
    lenisRef.current = lenis;

    let frameId: number;
    function raf(time: number) {
      lenis.raf(time);
      frameId = requestAnimationFrame(raf);
    }
    frameId = requestAnimationFrame(raf);

    return () => {
      cancelAnimationFrame(frameId);
      lenis.destroy();
      lenisRef.current = null;
    };
  }, []);

  return lenisRef;
}
