<div align="center">

# Rinti AI

**A chat workspace with per-user memory, a cited research mode and real account sessions.**

<br />

<table>
  <tr>
    <td align="center"><img src="docs/screenshots/login.webp" alt="Rinti sign-in screen: Welcome back, with email and password fields and an orb" width="320" /><br /><sub>Sign in</sub></td>
    <td align="center"><img src="docs/screenshots/register.webp" alt="Rinti create-account screen with name, email, password and confirm fields" width="320" /><br /><sub>Create an account</sub></td>
  </tr>
</table>
<sub>The only screens that render without the backend. Everything behind sign-in needs the API running.</sub>

<br />
<br />

![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=flat-square&logo=nextdotjs&logoColor=white) ![React](https://img.shields.io/badge/React-19-20232a?style=flat-square&logo=react&logoColor=white) ![TypeScript](https://img.shields.io/badge/TypeScript-5-3178c6?style=flat-square&logo=typescript&logoColor=white) ![Tailwind](https://img.shields.io/badge/Tailwind-3-06b6d4?style=flat-square&logo=tailwindcss&logoColor=white) ![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?style=flat-square&logo=fastapi&logoColor=white) ![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

<br />

**[Run it](#run-it)** &nbsp;·&nbsp; **[Features](#features)** &nbsp;·&nbsp; **[Architecture](#architecture)** &nbsp;·&nbsp; **[Installation](#installation)** &nbsp;·&nbsp; **[API](#api)**

</div>

---

Rinti AI pairs an OpenAI-compatible chat backend (Groq by default) with a research engine that plans sub-queries, searches, extracts sources and synthesises a cited answer, instead of just forwarding a prompt. There is no sign-in: every request runs as one shared local user, and state-changing routes still require an `X-Rinti-Client` header as CSRF mitigation. Because the model and search keys are shared server-side, usage is capped per day.

The backend is FastAPI with SQLite for local development and Postgres in production; the frontend is Next.js with a light and dark interface: a landing hero that turns into the conversation when you send your first message.

## Run it

You need an OpenAI-compatible API key (Groq works), and a Tavily key for research mode.

```bash
git clone https://github.com/Samudra-GITHub/Rinti-Ai.git
cd Rinti-Ai/backend && python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
uvicorn main:app --reload        # needs backend/.env, see Installation
```

```bash
cd Rinti-Ai/frontend && npm install && npm run dev
```

The frontend calls same-origin `/api/*`, which only `vercel.json` routes to the backend. There is no local proxy in the repo, so a local full-stack run needs `/api/*` on port 3000 routed to port 8000 (for example with the Vercel CLI).

## Features

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>Streaming chat</h3>
      <p>Streaming replies from an OpenAI-compatible endpoint, with saved conversations you can list, reopen and delete, and a model selector that lists what the backend reports as available.</p>
    </td>
    <td width="50%" valign="top">
      <h3>Memory</h3>
      <p>Per-user memory items you can list, add and delete, kept in SQLite locally or Postgres in production.</p>
    </td>
  </tr>
  <tr>
    <td width="50%" valign="top">
      <h3>Research mode</h3>
      <p>Quick and Standard budgets. Intent detection, query planning, Tavily search, page extraction (trafilatura and BeautifulSoup), claim evaluation and synthesis, rendered with a sources panel and inline citations.</p>
    </td>
    <td width="50%" valign="top">
      <h3>Reading and writing experience</h3>
      <p>Markdown replies with highlighted code blocks and tables, a growing composer (Enter sends, Shift+Enter adds a line), Stop, Regenerate, copy, and history grouped by date. Light, dark or system theme, and reduced-motion support.</p>
    </td>
  </tr>
</table>

**Also:** per-user daily caps on chat messages and research queries; an ambient animated background that pauses when hidden and turns off for reduced motion.

## Tech stack

| Layer | Technology |
| :-- | :-- |
| Backend | FastAPI, Uvicorn, Pydantic and pydantic-settings, the `openai` client, Argon2, trafilatura, BeautifulSoup |
| Storage | SQLite locally, Postgres in production (`psycopg2`) |
| Frontend | Next.js 15 (App Router), React 19, TypeScript 5, Tailwind CSS 3, Framer Motion, react-markdown with highlight.js |
| Services | Groq or any OpenAI-compatible LLM, Tavily search |

## Architecture

```mermaid
flowchart LR
    B[Browser] --> F[Next.js frontend]
    F -->|/api/*| A[FastAPI backend]
    A --> L[LLM<br/>Groq / OpenAI-compatible]
    A --> T[Tavily search]
    A --> D[(SQLite / Postgres)]
```

The browser only talks to the Next.js origin. Chat replies follow one response policy defined in `backend/core/personality.py`, so style changes happen in one place. Research runs as a pipeline (intent, plan, search, extract, evaluate, synthesise) with a budget per mode in `backend/research/config.py`.

```text
Rinti-Ai/
├── backend/
│   ├── main.py          FastAPI app, CORS, router registration
│   ├── config.py        Environment-driven settings
│   ├── api/             auth, chat, memory, research, settings, health, voice
│   ├── auth/            Password hashing, session and CSRF dependencies
│   ├── core/            Chat "brain" and personality
│   ├── memory/          SQLite and Postgres persistence
│   ├── research/        intent, planner, engine, evaluator, claims, synthesis, providers/, extractors/
│   ├── voice/           Speech helpers (router not mounted, see below)
│   └── scripts/         migrate_sqlite_to_postgres.py
├── frontend/
│   ├── app/             (app)/ landing + chat (one screen), memory, models, settings
│   └── components/  hooks/  providers/  lib/  ui/  styles/  middleware.ts
├── vercel.json          Frontend and backend services, /api routing
└── docs/screenshots/
```

### API

All routes are under `/api`.

| Area | Routes |
| :-- | :-- |
| Auth | `POST /auth/register`, `/auth/login`, `/auth/logout`; `GET /auth/me` |
| Chat | `POST /chat`, `POST /chat/stream`; `GET /conversations`, `GET` and `DELETE /conversations/{id}`; `GET /usage` |
| Memory | `GET` and `POST /memory`, `DELETE /memory/{id}` |
| Research | `GET /research/status`, `POST /research/intent`, `POST /research/stream` |
| Settings | `GET /settings`, `/voices`, `/models` |
| Health | `GET /health` |

The speech code in `backend/voice/` and `backend/api/voice.py` exists, but the voice router is not registered in `main.py`, so those endpoints are not served. Text-to-speech is a stub that returns empty audio.

## Installation

Requires Python 3, Node.js and npm.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate           # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload        # http://localhost:8000
```

```bash
cd frontend
npm install
npm run dev                      # http://localhost:3000
```

### Environment

Variables are read from `backend/.env`. Never commit it.

| Variable | Purpose | Default |
| :-- | :-- | :-- |
| `RINTI_DEFAULT_PROVIDER` | `groq` (cloud) or `ollama` (local models) | `groq` |
| `RINTI_CLOUD_FALLBACK` | Let the cloud answer if the local model fails, in Auto mode (`false` = the cloud is never used as a fallback). Changeable in Settings | `false` |
| `RINTI_COMMERCIAL_USE` | Only suggest models whose licence permits commercial use (Apache-2.0, MIT) | `false` |
| `RINTI_HARDWARE_CHECK` | Refuse, with an explanation, a local model that clearly can't fit this computer's memory | `true` |
| `RINTI_OLLAMA_BASE_URL` | Where Ollama listens | `http://127.0.0.1:11434` |
| `RINTI_DEFAULT_MODEL` | Everyday local model | `qwen2.5:7b` |
| `RINTI_CODING_MODEL` | Optional separate local model for programming questions | the everyday model |
| `RINTI_LOCAL_NUM_CTX` | Largest context window requested from Ollama; lowered automatically if this computer can't hold it | `8192` |
| `RINTI_ADMIN_TOKEN` | Allows changing inference settings from outside this machine | unset |
| `OPENAI_API_KEY` | Groq or OpenAI-compatible API key (optional for local-only use) | none |
| `OPENAI_BASE_URL` | LLM endpoint | `https://api.groq.com/openai/v1` |
| `TAVILY_API_KEY` | Required for research mode | none |
| `ENVIRONMENT` | `production` makes `DATABASE_URL` mandatory at startup | `development` |
| `DATABASE_URL` | Postgres connection string | unset, so SQLite is used |
| `DB_PATH` | SQLite file when `DATABASE_URL` is unset | `rinti_memory.db` |
| `ALLOWED_ORIGINS` | Comma-separated CORS allowlist | `http://localhost:3000,http://127.0.0.1:3000` |
| `MAX_CHAT_MESSAGES_PER_DAY` | Per-user chat cap | `40` |
| `MAX_RESEARCH_QUERIES_PER_DAY` | Per-user research cap | `8` |
| `MAX_RESPONSE_TOKENS` | Safety ceiling for one chat reply (length is governed by the response policy, not this) | `4096` |
| `HOST`, `PORT` | Server bind | `0.0.0.0`, `8000` |

### Deploy

`vercel.json` defines a `frontend` service (Next.js, `frontend/`) and a `backend` service (`main:app`, 60 s max duration) and routes `/api/*` to the backend. In production set `ENVIRONMENT=production` and `DATABASE_URL`, because Vercel Functions have no durable filesystem for SQLite. `backend/scripts/migrate_sqlite_to_postgres.py` migrates existing data.

### Local models

Rinti can answer from a model on your own computer through Ollama, with the cloud
as an optional fallback. See [docs/LOCAL_INFERENCE.md](docs/LOCAL_INFERENCE.md)
for setup, hardware-aware model suggestions, licences, the model comparison,
routing rules and cost trade-offs, and
`backend/scripts/benchmark.py` to measure models yourself.

## Limitations

- Voice endpoints are not mounted, and text-to-speech returns empty audio.
- Automated tests cover the backend inference layer (`cd backend && python -m pytest`); there are no frontend tests.
- Screenshots cover only the sign-in and register screens, because everything else needs the backend.

## License

[MIT](LICENSE).
