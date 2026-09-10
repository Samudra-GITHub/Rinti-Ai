"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { ModelProvider } from "@/providers/ModelProvider";
import { ConversationsProvider } from "@/providers/ConversationsProvider";
import { AppShell } from "@/components/layout/AppShell";
import { RintiOrb } from "@/components/orb/RintiOrb";

/**
 * Authenticated app shell. Client-side redirect here is a UX convenience
 * only — every request this shell's children make still goes through the
 * backend's own get_current_user check, which is the actual security
 * boundary (see middleware.ts for the note on why client-side protection
 * alone is never sufficient).
 */
function AuthGate({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [isLoading, user, router]);

  if (isLoading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <RintiOrb size="md" active />
      </div>
    );
  }

  return <>{children}</>;
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate>
      <ModelProvider>
        <ConversationsProvider>
          <AppShell>{children}</AppShell>
        </ConversationsProvider>
      </ModelProvider>
    </AuthGate>
  );
}
