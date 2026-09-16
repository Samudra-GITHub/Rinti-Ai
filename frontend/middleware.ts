import { NextResponse, type NextRequest } from "next/server";

// UX-only redirect layer. This does NOT validate the session — it only
// checks whether a session cookie is present, so it can bounce an obviously
// logged-out browser away from the app shell before the page even renders,
// avoiding a flash of protected content. The actual security boundary is
// server-side: every protected FastAPI route independently calls
// get_current_user and rejects an invalid/expired/revoked session regardless
// of what this middleware decided. A forged or stale cookie that passes this
// check still gets a real 401 from the backend.
//
// Deliberately does NOT redirect away from /login or /register just because a
// cookie is present — cookie *presence* isn't validity, and a stale/revoked
// cookie (e.g. its session row got deleted server-side) would otherwise
// produce an infinite loop: middleware bounces /login -> / because a cookie
// exists, the client's real /api/auth/me check comes back 401, AuthGate
// redirects back to /login, middleware bounces it to / again, forever. The
// "already logged in, skip the login page" convenience is handled client-side
// instead (see app/(auth)/layout.tsx), where it's based on a real /me result.
function hasSessionCookie(req: NextRequest): boolean {
  return req.cookies.getAll().some((c) => c.name === "rinti_session" || c.name === "__Host-rinti_session");
}

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  if (pathname === "/login" || pathname === "/register") {
    return NextResponse.next();
  }

  if (!hasSessionCookie(req)) {
    return NextResponse.redirect(new URL("/login", req.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Everything except:
     *  - /api/*       (backend proxy — the backend itself enforces auth)
     *  - /_next/*     (Next.js internals/assets)
     *  - favicon.ico
     */
    "/((?!api|_next|favicon.ico).*)",
  ],
  // This middleware only reads a cookie name and issues a redirect — no Edge
  // APIs needed — so it runs fine on the Node.js runtime. That's required
  // here: this project's Vercel deployment builds frontend/ and backend/ as
  // services in one project, and Vercel's services model doesn't support an
  // Edge Function (the default runtime for middleware) alongside them.
  runtime: "nodejs",
};
