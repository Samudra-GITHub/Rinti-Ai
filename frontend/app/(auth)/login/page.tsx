"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff, AlertCircle, ArrowRight } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { AuthError } from "@/lib/auth";
import { RintiOrb } from "@/components/orb/RintiOrb";
import { Button } from "@/ui/Button";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (isSubmitting) return;
    setError(null);
    setIsSubmitting(true);
    try {
      await login(email.trim(), password);
      router.replace("/");
    } catch (err) {
      setError(err instanceof AuthError ? err.message : "Could not log in. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="glass-panel relative w-full max-w-sm rounded-2xl p-8">
      <div className="flex flex-col items-center text-center">
        <RintiOrb size="md" />
        <h1 className="mt-4 text-lg font-semibold text-white/95">Welcome back</h1>
        <p className="mt-1 text-sm text-white/45">Sign in to continue with Rinti.</p>
      </div>

      <form onSubmit={handleSubmit} className="mt-8 flex flex-col gap-4" noValidate>
        <div className="flex flex-col gap-1.5">
          <label htmlFor="email" className="text-xs font-medium text-white/55">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="glass-inset w-full rounded-xl px-3.5 py-2.5 text-sm text-white/90 placeholder:text-white/25 outline-none transition-colors focus:border-purple-400/40 focus-ring"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="password" className="text-xs font-medium text-white/55">
            Password
          </label>
          <div className="relative">
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="glass-inset w-full rounded-xl px-3.5 py-2.5 pr-10 text-sm text-white/90 placeholder:text-white/25 outline-none transition-colors focus:border-purple-400/40 focus-ring"
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-full p-1 text-white/35 hover:text-white/70 focus-ring"
            >
              {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
            </button>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 rounded-xl border border-red-400/25 bg-red-500/10 px-3.5 py-2.5 text-xs text-red-200">
            <AlertCircle size={13} className="shrink-0" />
            {error}
          </div>
        )}

        <Button type="submit" variant="primary" size="md" disabled={isSubmitting} className="mt-1 w-full">
          {isSubmitting ? "Signing in…" : "Sign in"}
          {!isSubmitting && <ArrowRight size={15} />}
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-white/40">
        New to Rinti?{" "}
        <Link href="/register" className="text-purple-300 hover:text-purple-200 focus-ring">
          Create an account
        </Link>
      </p>
    </div>
  );
}
