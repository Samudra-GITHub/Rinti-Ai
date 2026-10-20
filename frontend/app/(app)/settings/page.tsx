"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowUpRight, Monitor, Moon, Sun } from "lucide-react";
import { PageShell, SectionLabel } from "@/components/layout/PageShell";
import { SettingsCard } from "@/components/settings/SettingsCard";
import { Segmented } from "@/ui/Segmented";
import { Switch } from "@/ui/Switch";
import { useTheme, } from "@/hooks/useTheme";
import { useActiveModel } from "@/hooks/useActiveModel";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const { theme, setTheme, reduceMotion, setReduceMotion, showTimestamps, setShowTimestamps } = useTheme();
  const { activeModel } = useActiveModel();

  // "Use memory" is stored by the backend and really changes Rinti's replies.
  const [memoryEnabled, setMemoryEnabled] = useState<boolean | null>(null);
  const [memoryError, setMemoryError] = useState<string | null>(null);
  const [savingMemory, setSavingMemory] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .getSettings()
      .then((s) => {
        if (!cancelled) setMemoryEnabled(s.memory_enabled);
      })
      .catch((e) => {
        if (!cancelled) setMemoryError(e instanceof Error ? e.message : "Couldn't load this setting.");
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleMemoryToggle(next: boolean) {
    const previous = memoryEnabled;
    setMemoryEnabled(next);
    setSavingMemory(true);
    setMemoryError(null);
    try {
      const saved = await api.updateSettings({ memory_enabled: next });
      setMemoryEnabled(saved.memory_enabled);
    } catch (e) {
      setMemoryEnabled(previous);
      setMemoryError(e instanceof Error ? e.message : "Couldn't save this setting. Try again.");
    } finally {
      setSavingMemory(false);
    }
  }

  return (
    <PageShell title="Settings" description="Appearance is saved in this browser. Memory is saved on the server.">
      <SectionLabel>Appearance</SectionLabel>
      <SettingsCard title="Theme" description="Follow your system, or always use light or dark.">
        <Segmented
          label="Theme"
          value={theme}
          onChange={setTheme}
          options={[
            { value: "system", label: "System", icon: <Monitor size={13} /> },
            { value: "light", label: "Light", icon: <Sun size={13} /> },
            { value: "dark", label: "Dark", icon: <Moon size={13} /> },
          ]}
        />
      </SettingsCard>
      <SettingsCard
        title="Reduce motion"
        description="Turn off the background animation and most transitions. Your system's reduced-motion setting is always respected."
      >
        <Switch checked={reduceMotion} onCheckedChange={setReduceMotion} label="Reduce motion" />
      </SettingsCard>

      <SectionLabel>Conversations</SectionLabel>
      <SettingsCard title="Show message times" description="Display the time each message was sent.">
        <Switch checked={showTimestamps} onCheckedChange={setShowTimestamps} label="Show message times" />
      </SettingsCard>

      <SectionLabel>Memory</SectionLabel>
      <SettingsCard
        title="Use memory in replies"
        description="Let Rinti draw on the facts you've saved to personalise its answers."
      >
        {memoryEnabled === null && !memoryError ? (
          <div className="h-6 w-11 animate-pulse rounded-full bg-fg/10" aria-label="Loading" />
        ) : (
          <Switch
            checked={Boolean(memoryEnabled)}
            onCheckedChange={handleMemoryToggle}
            label="Use memory in replies"
            disabled={memoryEnabled === null || savingMemory}
          />
        )}
      </SettingsCard>
      {memoryError && (
        <p role="alert" className="px-1 pb-2 text-[13px] text-red-600 dark:text-red-300">
          {memoryError}
        </p>
      )}
      <Link
        href="/memory"
        className="mt-1 inline-flex items-center gap-1 px-1 text-[13px] text-purple-300 hover:underline focus-ring"
      >
        Manage what Rinti remembers <ArrowUpRight size={13} />
      </Link>

      <SectionLabel>Model</SectionLabel>
      <SettingsCard
        title="Active model"
        description={activeModel ? `Rinti is using ${activeModel}.` : "No model is available right now."}
      >
        <Link href="/models" className="text-[13px] text-purple-300 hover:underline focus-ring">
          Change
        </Link>
      </SettingsCard>
    </PageShell>
  );
}
