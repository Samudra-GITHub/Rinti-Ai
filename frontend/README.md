# Rinti AI frontend

Next.js 15 (App Router) client for Rinti AI. See the [root README](../README.md) for the full project overview, configuration and deployment notes.

```bash
npm install
npm run dev      # http://localhost:3000
npm run build
npm run lint
```

The app calls same-origin `/api/*`, which `vercel.json` routes to the FastAPI backend in production.
