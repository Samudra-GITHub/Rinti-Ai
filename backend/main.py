from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import memory.database as db
from memory import db_backend
from api import auth as auth_api, chat, health, memory as memory_api, research, settings as settings_api
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        db.init_db()
    except Exception as exc:
        import sys
        print(f"FATAL: database initialization failed during startup: {exc}", file=sys.stderr)
        raise
    yield
    db_backend.close_pool()


app = FastAPI(title="Rinti AI Companion Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(auth_api.router, prefix="/api")
app.include_router(chat.router, prefix="/api")
app.include_router(memory_api.router, prefix="/api")
app.include_router(research.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")
