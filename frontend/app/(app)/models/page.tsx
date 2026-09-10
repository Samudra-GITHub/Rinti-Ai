"use client";

import { ModelCard } from "@/components/models/ModelCard";
import { ModelSelector } from "@/components/models/ModelSelector";
import { useActiveModel } from "@/hooks/useActiveModel";

export default function ModelsPage() {
  const { activeModel, setActiveModel, availableModels, isLoading, error } = useActiveModel();

  return (
    <div className="mx-auto max-w-6xl py-6">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-white/95">Models</h1>
          <p className="mt-1 text-sm text-white/45">
            Models the backend reports as configured and available.
          </p>
        </div>
        <ModelSelector />
      </div>

      {isLoading ? (
        <p className="text-sm text-white/40">Loading models…</p>
      ) : error ? (
        <p className="rounded-xl border border-red-400/25 bg-red-500/10 px-4 py-2.5 text-sm text-red-200">
          {error}
        </p>
      ) : availableModels.length === 0 ? (
        <p className="text-sm text-white/40">
          No model is currently available — check the backend&apos;s provider configuration.
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {availableModels.map((model) => (
            <ModelCard
              key={model.id}
              model={model}
              active={model.id === activeModel}
              onSelect={setActiveModel}
            />
          ))}
        </div>
      )}
    </div>
  );
}
