"use client";

import { Menu } from "lucide-react";
import { ConversationSidebar } from "@/components/navigation/ConversationSidebar";
import { GradientBackground } from "@/common/GradientBackground";
import { ThemeToggle } from "@/common/ThemeToggle";
import { IconButton } from "@/ui/IconButton";
import { useSidebar } from "@/hooks/useSidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const sidebar = useSidebar(true);

  return (
    <div className="relative flex min-h-screen">
      <GradientBackground />
      <ConversationSidebar isOpen={sidebar.isOpen} onClose={sidebar.close} />

      <div className="flex min-h-screen flex-1 flex-col">
        <header className="flex items-center justify-between px-6 py-4 lg:px-8">
          <IconButton
            icon={Menu}
            aria-label={sidebar.isOpen ? "Collapse sidebar" : "Expand sidebar"}
            onClick={sidebar.toggle}
          />
          <ThemeToggle />
        </header>

        <main className="flex-1 px-6 pb-8 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
