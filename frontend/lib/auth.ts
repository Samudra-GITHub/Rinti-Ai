// Auth client. Same-origin only — every call goes through this app's own
// /api/auth/* path (proxied by app/api/[...path]/route.ts), which is what
// lets the backend's HttpOnly session cookie land scoped to this app's own
// origin. Nothing here ever touches localStorage/sessionStorage: the session
// lives entirely in that cookie, which this code can't even read.
import { withCsrfHeader } from "@/lib/http";

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  created_at: string;
  updated_at?: string | null;
}

export class AuthError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseErrorDetail(res: Response, fallback: string): Promise<string> {
  if (res.status >= 500) return "Something went wrong on the server. Please try again.";
  try {
    const body = await res.json();
    if (typeof body?.detail === "string") return body.detail;
  } catch {
    // ignore non-JSON bodies
  }
  return fallback;
}

export async function fetchCurrentUser(): Promise<AuthUser | null> {
  let res: Response;
  try {
    res = await fetch("/api/auth/me", { headers: { "Content-Type": "application/json" } });
  } catch {
    return null;
  }
  if (res.status === 401) return null;
  if (!res.ok) return null;
  return (await res.json()) as AuthUser;
}

export async function registerUser(name: string, email: string, password: string): Promise<AuthUser> {
  const res = await fetch("/api/auth/register", {
    method: "POST",
    headers: withCsrfHeader({ "Content-Type": "application/json" }),
    body: JSON.stringify({ name, email, password }),
  });
  if (!res.ok) throw new AuthError(res.status, await parseErrorDetail(res, "Could not create account."));
  return (await res.json()) as AuthUser;
}

export async function loginUser(email: string, password: string): Promise<AuthUser> {
  const res = await fetch("/api/auth/login", {
    method: "POST",
    headers: withCsrfHeader({ "Content-Type": "application/json" }),
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new AuthError(res.status, await parseErrorDetail(res, "Could not log in."));
  return (await res.json()) as AuthUser;
}

export async function logoutUser(): Promise<void> {
  await fetch("/api/auth/logout", {
    method: "POST",
    headers: withCsrfHeader(),
  }).catch(() => {
    // Best-effort: even if this fails, clearing client state below still
    // logs the user out of this tab; the cookie naturally expires anyway.
  });
}
