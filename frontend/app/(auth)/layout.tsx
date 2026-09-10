"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { GradientBackground } from "@/common/GradientBackground";
import { RintiOrb } from "@/components/orb/RintiOrb";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && user) router.replace("/");
  }, [isLoading, user, router]);

  // Loading, or already authenticated and about to be redirected — either
  // way, don't flash the login form.
  if (isLoading || user) {
    return (
      <div className="relative flex min-h-screen items-center justify-center">
        <GradientBackground />
        <RintiOrb size="md" active />
      </div>
    );
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center px-4 py-10">
      <GradientBackground />
      {children}
    </div>
  );
}
