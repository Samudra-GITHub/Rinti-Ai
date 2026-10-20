import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Local dev only: on Vercel, vercel.json routes /api/* to the backend
  // service. Without this, `npm run dev` has nothing serving /api/*.
  async rewrites() {
    if (process.env.NODE_ENV === "production") return [];
    const backend = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${backend}/api/:path*` }];
  },
};

export default nextConfig;
