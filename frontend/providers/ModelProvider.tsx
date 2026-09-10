"use client";

import { createContext, useCallback, useEffect, useMemo, useState } from "react";
import { api, type ModelAvailabilityDto } from "@/lib/api";

interface ModelContextValue {
  activeModel: string | null;
  setActiveModel: (id: string) => void;
  availableModels: ModelAvailabilityDto[];
  isLoading: boolean;
  error: string | null;
}

export const ModelContext = createContext<ModelContextValue | null>(null);

const STORAGE_KEY = "rinti-active-model";

export function ModelProvider({ children }: { children: React.ReactNode }) {
  const [availableModels, setAvailableModels] = useState<ModelAvailabilityDto[]>([]);
  const [activeModel, setActiveModelState] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    api
      .listModels()
      .then((data) => {
        if (cancelled) return;
        // Only ever show what the backend reports as actually available — never a
        // fabricated Claude/Gemini/Perplexity option the backend doesn't serve.
        const available = data.filter((m) => m.available);
        setAvailableModels(available);

        let stored: string | null = null;
        try {
          stored = window.localStorage.getItem(STORAGE_KEY);
        } catch {
          // ignore unavailable storage
        }
        const validStored = stored && available.some((m) => m.id === stored) ? stored : null;
        setActiveModelState(validStored ?? available[0]?.id ?? null);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load models");
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const setActiveModel = useCallback((id: string) => {
    setActiveModelState(id);
    try {
      window.localStorage.setItem(STORAGE_KEY, id);
    } catch {
      // ignore unavailable storage
    }
  }, []);

  const value = useMemo(
    () => ({ activeModel, setActiveModel, availableModels, isLoading, error }),
    [activeModel, setActiveModel, availableModels, isLoading, error]
  );

  return <ModelContext.Provider value={value}>{children}</ModelContext.Provider>;
}
