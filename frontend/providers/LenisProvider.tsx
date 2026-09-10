"use client";

import { useLenisScroll } from "@/hooks/useLenisScroll";

export function LenisProvider({ children }: { children: React.ReactNode }) {
  useLenisScroll();
  return <>{children}</>;
}
