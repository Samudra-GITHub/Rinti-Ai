"use client";

import { ModelCard } from "@/components/models/ModelCard";
import { PageShell } from "@/components/layout/PageShell";
import { useActiveModel } from "@/hooks/useActiveModel";

export default function ModelsPage() {
  const { activeModel, setActiveModel, availableModels, isLoading, error } = useActiveModel();

  return (
    <PageShell title="Models" description="The models the server reports as configured and ready to use.">
      {isLoading ? (
        <div className="space-y-3" role="status" aria-label="Loading models">
          <div className="h-[4.25rem] animate-pulse rounded-2xl bg-fg/[0.05]" />
        </div>
      ) : error ? (
        <p
          role="alert"
          className="rounded-2xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm text-red-700 dark:text-red-200"
        >
          {error}
        </p>
      ) : availableModels.length === 0 ? (
        <div className="rounded-2xl border border-fg/10 px-5 py-8 text-center">
          <p className="text-sm text-fg/70">No model is available right now.</p>
          <p className="mt-1 text-[13px] text-fg/40">Check that the server has an API key configured for its model provider.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {availableModels.map((model) => (
            <ModelCard key={model.id} model={model} active={model.id === activeModel} onSelect={setActiveModel} />
          ))}
        </div>
      )}
    </PageShell>
  );
}
