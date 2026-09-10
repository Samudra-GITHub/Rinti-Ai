"use client";

import { useContext } from "react";
import { ModelContext } from "@/providers/ModelProvider";

export function useActiveModel() {
  const ctx = useContext(ModelContext);
  if (!ctx) {
    throw new Error("useActiveModel must be used within a ModelProvider");
  }
  return ctx;
}
