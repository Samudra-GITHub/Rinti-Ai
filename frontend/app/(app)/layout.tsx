"use client";

import { ModelProvider } from "@/providers/ModelProvider";
import { ConversationsProvider } from "@/providers/ConversationsProvider";
import { AppShell } from "@/components/layout/AppShell";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <ModelProvider>
      <ConversationsProvider>
        <AppShell>{children}</AppShell>
      </ConversationsProvider>
    </ModelProvider>
  );
}
