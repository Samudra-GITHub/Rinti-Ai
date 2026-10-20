import { NextResponse } from "next/server";

// Login is disabled; every route is open.
export function middleware() {
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next|favicon.ico).*)"],
  // Node.js runtime: Vercel's services model doesn't support Edge middleware
  // alongside the backend service.
  runtime: "nodejs",
};
