// Same-origin proxy for every non-streaming /api/* call (auth, conversations,
// memory, models, settings, research status/intent/session lookups). Chat and
// research *streaming* have their own route handlers (app/api/chat,
// app/api/research) because SSE needs the response body piped through as it
// arrives rather than buffered here.
//
// This is the one place responsible for carrying the session cookie between
// the browser and FastAPI in both directions: the browser's Cookie header is
// forwarded to the backend on the way in, and the backend's Set-Cookie
// header(s) are forwarded back to the browser on the way out. Because the
// browser only ever talks to this same-origin route (never to the FastAPI
// origin directly), a cookie the backend sets here is scoped to this app's
// own origin — exactly what makes an HttpOnly session cookie usable at all
// in a split frontend/backend dev setup.
export const runtime = "nodejs";

const BACKEND_URL = process.env.RINTI_BACKEND_URL ?? "http://127.0.0.1:8000";

const HOP_BY_HOP_REQUEST_HEADERS = new Set(["host", "connection", "content-length"]);
const HOP_BY_HOP_RESPONSE_HEADERS = new Set([
  "connection",
  "content-length",
  "transfer-encoding",
  "content-encoding",
]);

async function proxy(req: Request, path: string[]): Promise<Response> {
  const url = new URL(req.url);
  const target = `${BACKEND_URL}/api/${path.join("/")}${url.search}`;

  const headers = new Headers();
  req.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_REQUEST_HEADERS.has(key.toLowerCase())) headers.set(key, value);
  });

  const hasBody = req.method !== "GET" && req.method !== "HEAD";

  let upstream: Response;
  try {
    upstream = await fetch(target, {
      method: req.method,
      headers,
      body: hasBody ? await req.text() : undefined,
      redirect: "manual",
    });
  } catch {
    return Response.json({ detail: "Can't reach Rinti's backend. Is it running?" }, { status: 502 });
  }

  const resHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!HOP_BY_HOP_RESPONSE_HEADERS.has(key.toLowerCase())) resHeaders.append(key, value);
  });
  // fetch() Headers collapses multiple Set-Cookie into one on read unless
  // accessed via getSetCookie() (Node 18.17+ / undici) — use it explicitly so
  // a response that both rotates the session and sets another cookie doesn't
  // lose one of them.
  resHeaders.delete("set-cookie");
  const setCookies =
    typeof (upstream.headers as Headers & { getSetCookie?: () => string[] }).getSetCookie === "function"
      ? (upstream.headers as Headers & { getSetCookie: () => string[] }).getSetCookie()
      : [];
  for (const cookie of setCookies) resHeaders.append("set-cookie", cookie);

  const buffer = await upstream.arrayBuffer();
  return new Response(buffer, { status: upstream.status, headers: resHeaders });
}

type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(req: Request, ctx: RouteContext) {
  return proxy(req, (await ctx.params).path);
}
export async function POST(req: Request, ctx: RouteContext) {
  return proxy(req, (await ctx.params).path);
}
export async function PATCH(req: Request, ctx: RouteContext) {
  return proxy(req, (await ctx.params).path);
}
export async function DELETE(req: Request, ctx: RouteContext) {
  return proxy(req, (await ctx.params).path);
}
