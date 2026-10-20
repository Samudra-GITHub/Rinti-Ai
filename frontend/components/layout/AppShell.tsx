"use client";

import { Suspense } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { PanelLeftOpen } from "lucide-react";
import { ConversationSidebar } from "@/components/navigation/ConversationSidebar";
import { AmbientBackground } from "@/components/ambient/AmbientBackground";
import { ModelSelector } from "@/components/models/ModelSelector";
import { ThemeToggle } from "@/common/ThemeToggle";
import { IconButton } from "@/ui/IconButton";
import { useSidebar } from "@/hooks/useSidebar";

/**
 * The full scene is for the empty landing state; a quieter version sits behind
 * an open conversation and the utility pages.
 */
function RouteAmbient() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const isLanding = (pathname === "/" || pathname === "/chat") && !searchParams.get("c");
  return <AmbientBackground intensity={isLanding ? "hero" : "calm"} />;
}

/**
 * The page is a dark ground with the navigation docked on it and the work
 * area framed as one large rounded "stage" (hairline border, lit top edge),
 * as in the reference. On small screens the stage goes edge to edge.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const sidebar = useSidebar();

  return (
    <div className="dvh-screen flex overflow-hidden bg-page lg:p-3">
      <ConversationSidebar isOpen={sidebar.isOpen} isDesktop={sidebar.isDesktop} onClose={sidebar.close} />

      <div className="stage flex min-w-0 flex-1 flex-col max-lg:rounded-none max-lg:border-0 lg:rounded-[1.75rem]">
        <Suspense fallback={<AmbientBackground intensity="hero" />}>
          <RouteAmbient />
        </Suspense>

        <header className="pt-safe relative z-10 flex h-14 shrink-0 items-center gap-2 px-3 sm:px-4">
          {!sidebar.isOpen && (
            <IconButton icon={PanelLeftOpen} aria-label="Open sidebar" appearance="bare" onClick={sidebar.toggle} />
          )}
          <ModelSelector />
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </header>

        <main className="relative z-10 min-h-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
