# Rinti AI

**Your intelligent AI workspace.**

A conversational AI assistant with persistent memory, a multi-step research mode, and account-based sessions — built on a FastAPI backend and a Next.js frontend.

<br/>

<img src="./assets/hero-placeholder.svg" width="100%" alt="Rinti AI hero" />

<br/>

## Overview

Rinti AI pairs a Groq/OpenAI-compatible chat backend with a research engine that plans searches, extracts sources, and synthesizes findings rather than just forwarding a prompt. Sessions are backed by real accounts — password auth with hashed credentials, HttpOnly session cookies, and CSRF protection — not a stub login screen.

<br/>

## Features

| Feature | Description |
|:--|:--|
| Chat | Streaming conversational responses over a Groq/OpenAI-compatible endpoint |
| Memory | Persistent, per-user conversation memory (`memory/` module, SQLite or Postgres) |
| Research mode | Multi-step research engine — query planning, budgeted search, source extraction, and synthesis (`research/`) |
| Authentication | Registration, login, logout, and session restoration via HttpOnly cookies + CSRF headers |
| Voice | Dedicated voice API surface (`api/voice.py`) |
| Settings | Per-user configurable settings |

<br/>

## Architecture

```
┌─────────────────┐       HTTPS        ┌──────────────────────┐
│  Next.js 15      │ ─────────────────▶ │  FastAPI backend      │
│  (frontend/)      │ ◀───────────────── │  (backend/)            │
└─────────────────┘     streaming        └───────────┬──────────┘
                                                       │
                          ┌────────────────────────────┼───────────────────────────┐
                          ▼                            ▼                           ▼
                 ┌────────────────┐          ┌──────────────────┐        ┌──────────────────┐
                 │ Groq / OpenAI-   │          │ Tavily search API  │        │ SQLite (dev) or   │
                 │ compatible LLM   │          │ (research mode)     │        │ Postgres (prod)    │
                 └────────────────┘          └──────────────────┘        └──────────────────┘
```

<br/>

## Providers

- **LLM** — any OpenAI-compatible endpoint; defaults to Groq (`OPENAI_BASE_URL`)
- **Search** — [Tavily](https://tavily.com) for research-mode source discovery
- **Persistence** — SQLite locally, Postgres in production (`DATABASE_URL`)

<br/>

## API Endpoints

| Route | Purpose |
|:--|:--|
| `POST /api/auth/*` | Register, login, logout, session restore |
| `POST /api/chat` | Streaming chat completions |
| `GET/POST /api/memory` | Read and write conversation memory |
| `POST /api/research` | Run a research-mode query |
| `GET/POST /api/settings` | Per-user settings |
| `POST /api/voice` | Voice interaction endpoint |
| `GET /api/health` | Health check |

<br/>

## Folder Structure

```
rinti-ai/
├── backend/
│   ├── api/            # auth, chat, health, memory, research, settings, voice
│   ├── auth/           # session + CSRF dependencies
│   ├── core/
│   ├── memory/         # SQLite/Postgres-backed conversation memory
│   ├── research/       # planner, engine, extractors, providers (Tavily), synthesis
│   ├── voice/
│   ├── config.py        # Settings (env-driven)
│   └── main.py
└── frontend/
    ├── app/
    │   ├── (app)/       # authenticated app routes
    │   └── (auth)/      # login / register routes
    ├── components/
    ├── hooks/
    ├── lib/
    └── providers/
```

<br/>

## Tech Stack

**Backend** — `FastAPI` · `Pydantic` · `psycopg2` (Postgres) · `argon2-cffi` (password hashing) · `trafilatura` + `BeautifulSoup` (extraction)
**Frontend** — `Next.js 15` · `React 19` · `TypeScript` · `Tailwind CSS` · `Framer Motion` · `Lenis`

<br/>

## Setup

**Backend**

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

<br/>

## Environment Variables

**Backend** (`backend/.env`)

```bash
OPENAI_API_KEY=          # your Groq or OpenAI-compatible API key
OPENAI_BASE_URL=https://api.groq.com/openai/v1
TAVILY_API_KEY=          # required for research mode
HOST=0.0.0.0
PORT=8000
ENVIRONMENT=development  # set to "production" to require DATABASE_URL
DB_PATH=rinti_memory.db  # used when DATABASE_URL is unset (local SQLite)
DATABASE_URL=            # Postgres connection string, required in production
```

<br/>

## Deployment

Configured for Vercel (`vercel.json` at repo root). In production, `ENVIRONMENT=production` requires `DATABASE_URL` to be set — Vercel Functions have no durable local filesystem, so SQLite can't back production data there.

<br/>

## Roadmap

- [x] Chat with streaming responses
- [x] Persistent memory
- [x] Multi-step research mode
- [x] Session-based authentication
- [x] Voice API surface
- [ ] Richer memory recall across long sessions
- [ ] Expanded provider support beyond Groq/OpenAI

<br/>

## License

MIT — see [LICENSE](./LICENSE).

<br/>

<sub>Part of the Samudra OS product ecosystem. See the [profile](https://github.com/Samudra-GITHub) for the full lineup.</sub>
