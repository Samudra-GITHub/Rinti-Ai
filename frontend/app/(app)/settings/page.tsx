"use client";

import { useState } from "react";
import { SettingsCard } from "@/components/settings/SettingsCard";
import { Switch } from "@/ui/Switch";
import { useTheme } from "@/hooks/useTheme";

export default function SettingsPage() {
  const { theme, toggleTheme } = useTheme();
  const [compact, setCompact] = useState(false);
  const [reduceMotion, setReduceMotion] = useState(false);
  const [sidebarPinned, setSidebarPinned] = useState(true);
  const [showTimestamps, setShowTimestamps] = useState(true);

  return (
    <div className="mx-auto max-w-2xl py-6">
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-white/95">Settings</h1>
        <p className="mt-1 text-sm text-white/45">
          Preferences are stored locally in this browser only.
        </p>
      </div>

      <div className="space-y-4">
        <p className="px-1 text-[11px] font-medium uppercase tracking-wider text-white/35">
          Appearance
        </p>
        <SettingsCard
          title="Dim variant"
          description="Switch between the deep-black theme and a softer, dimmer dark variant."
        >
          <Switch checked={theme === "dim"} onCheckedChange={toggleTheme} label="Toggle dim theme" />
        </SettingsCard>

        <SettingsCard
          title="Reduce motion"
          description="Minimize orb pulsing and transition animations across the app."
        >
          <Switch checked={reduceMotion} onCheckedChange={setReduceMotion} label="Toggle reduced motion" />
        </SettingsCard>

        <p className="px-1 pt-4 text-[11px] font-medium uppercase tracking-wider text-white/35">
          Layout
        </p>
        <SettingsCard
          title="Compact layout"
          description="Tighten spacing across cards and lists for smaller displays."
        >
          <Switch checked={compact} onCheckedChange={setCompact} label="Toggle compact layout" />
        </SettingsCard>

        <SettingsCard
          title="Keep sidebar pinned"
          description="Always show the conversation sidebar on desktop, even after navigating."
        >
          <Switch checked={sidebarPinned} onCheckedChange={setSidebarPinned} label="Toggle sidebar pinned" />
        </SettingsCard>

        <SettingsCard
          title="Show message timestamps"
          description="Display the time each message was sent inside chat bubbles."
        >
          <Switch checked={showTimestamps} onCheckedChange={setShowTimestamps} label="Toggle timestamps" />
        </SettingsCard>
      </div>
    </div>
  );
}
