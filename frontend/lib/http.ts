// Shared fetch wrapper for same-origin calls into this app's own /api/*
// routes (which proxy to the FastAPI backend — see app/api/[...path]/route.ts).
// Adds the header every state-changing backend request checks for; see
// backend/auth/dependencies.py:verify_csrf_header for why this is required
// and why it's a meaningful CSRF mitigation for a same-origin SPA+cookie API.
export const CSRF_HEADER_NAME = "X-Rinti-Client";
export const CSRF_HEADER_VALUE = "1";

export function withCsrfHeader(headers: HeadersInit = {}): HeadersInit {
  return { ...headers, [CSRF_HEADER_NAME]: CSRF_HEADER_VALUE };
}
