// Same-origin SSE proxy for research, mirroring app/api/chat/route.ts.
// The browser never talks to the provider or sees any provider credential —
// this route only forwards bytes to the FastAPI backend and streams them back.
export const runtime = "nodejs";

const BACKEND_URL = process.env.RINTI_BACKEND_URL ||
  (process.env.NODE_ENV === 'production' ? 'http://backend.internal' : 'http://127.0.0.1:8000');

function sseError(code: string, message: string) {
  return new Response(`event: error\ndata: ${JSON.stringify({ code, message })}\n\n`, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
    },
  });
}

export async function POST(req: Request) {
  let body: string;
  try {
    body = await req.text();
  } catch {
    return sseError("invalid_request", "Could not read the request body.");
  }

  const cookie = req.headers.get("cookie");

  let upstream: Response;
  try {
    upstream = await fetch(`${BACKEND_URL}/api/research/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Rinti-Client": "1",
        ...(cookie ? { cookie } : {}),
      },
      body,
    });
  } catch {
    return sseError("provider_unreachable", "Can't reach Rinti's backend right now.");
  }

  if (upstream.status === 401) {
    return sseError("unauthenticated", "Your session has expired. Please log in again.");
  }
  if (!upstream.ok || !upstream.body) {
    return sseError("backend_error", "The backend rejected the research request.");
  }

  const headers: Record<string, string> = {
    "Content-Type": "text/event-stream",
    "Cache-Control": "no-cache, no-transform",
    Connection: "keep-alive",
  };
  const conversationId = upstream.headers.get("x-conversation-id");
  if (conversationId) headers["X-Conversation-Id"] = conversationId;
  const sessionId = upstream.headers.get("x-research-session-id");
  if (sessionId) headers["X-Research-Session-Id"] = sessionId;

  return new Response(upstream.body, { status: 200, headers });
}
