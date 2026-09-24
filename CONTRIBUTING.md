# Contributing to Rinti AI

Thanks for considering a contribution. This is a two-part project — a FastAPI backend and a Next.js frontend — so set up both before opening a PR that touches either.

## Getting set up

```bash
git clone https://github.com/Samudra-GITHub/Rinti-Ai.git
cd Rinti-Ai

# backend
cd backend
pip install -r requirements.txt
cp .env.example .env   # fill in OPENAI_API_KEY and TAVILY_API_KEY at minimum
uvicorn main:app --reload

# frontend (separate terminal)
cd ../frontend
npm install
npm run dev
```

See the main [README](./README.md#environment-variables) for the full environment variable reference.

## Before opening a PR

**Backend**

```bash
python -m py_compile $(find backend -name "*.py")   # or your preferred lint/type-check setup
```

**Frontend**

```bash
npm run build
npm run lint
```

## Scope

- Backend changes belong in `backend/`, organized by domain (`api/`, `auth/`, `memory/`, `research/`, `voice/`).
- Frontend changes belong in `frontend/`, following the existing `(app)` / `(auth)` route group split.
- Changes to research-mode budgets or provider behavior should include a short rationale in the PR description — these are tuned against real rate limits, not arbitrary.

## Reporting issues

Use the issue templates under `.github/ISSUE_TEMPLATE/`.
