"""One-time data migration: copies existing local SQLite data into Postgres.

Usage (run from backend/):
    python scripts/migrate_sqlite_to_postgres.py

Reads the SQLite file at settings.db_path (same file local dev already uses)
and the Postgres database at DATABASE_URL (must be set in the environment),
then upserts every row table-by-table in FK-safe order: users -> sessions ->
conversations -> messages -> memories -> settings -> research_sessions ->
usage_daily.

Safety:
- Never deletes or modifies the SQLite file — it is opened read-only.
- Idempotent: every insert uses `ON CONFLICT (<pk>) DO NOTHING`, so re-running
  this script after partial progress (or after new SQLite rows were added)
  only inserts what's missing; it never overwrites rows already migrated.
- Preserves primary keys, foreign keys, and original timestamps exactly as
  stored in SQLite (no regenerated ids, no "migrated_at" rewriting).
- Requires the Postgres schema to already exist — run the app once against
  DATABASE_URL first (init_db() creates it), then run this script.
"""

import os
import sqlite3
import sys

import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings  # noqa: E402

TABLES_IN_FK_ORDER = [
    ("users", ["id", "name", "email", "password_hash", "created_at", "updated_at", "is_active"], "id"),
    ("sessions", ["id", "user_id", "token_hash", "created_at", "expires_at", "revoked_at", "last_seen_at"], "id"),
    ("conversations", ["id", "user_id", "title", "created_at", "updated_at"], "id"),
    ("messages", ["id", "conversation_id", "role", "content", "timestamp", "research_session_id"], "id"),
    ("memories", ["id", "user_id", "content", "category", "enabled", "created_at"], "id"),
    ("settings", ["id", "tts_enabled", "wake_word_enabled", "memory_enabled", "voice_id"], "id"),
    (
        "research_sessions",
        [
            "id", "conversation_id", "user_id", "query", "mode", "intent",
            "status", "partial", "result_json", "created_at", "updated_at",
        ],
        "id",
    ),
    ("usage_daily", ["user_id", "usage_date", "chat_count", "research_count"], "user_id, usage_date"),
]


def migrate() -> None:
    if not settings.database_url:
        print("DATABASE_URL is not set — nothing to migrate into. Aborting.")
        sys.exit(1)

    print(f"Source (SQLite, read-only): {settings.db_path}")
    print(f"Target (Postgres):          {settings.database_url.split('@')[-1]}")  # never print credentials

    src = sqlite3.connect(f"file:{settings.db_path}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    dst = psycopg2.connect(settings.database_url)

    try:
        for table, columns, conflict_key in TABLES_IN_FK_ORDER:
            src_cursor = src.cursor()
            try:
                src_cursor.execute(f"SELECT {', '.join(columns)} FROM {table}")
            except sqlite3.OperationalError as exc:
                print(f"  [{table}] skipped — not present in source SQLite DB ({exc})")
                continue
            rows = [tuple(row) for row in src_cursor.fetchall()]

            if not rows:
                print(f"  [{table}] 0 rows in source, nothing to do")
                continue

            placeholders = ", ".join(["%s"] * len(columns))
            insert_sql = (
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders}) "
                f"ON CONFLICT ({conflict_key}) DO NOTHING"
            )
            dst_cursor = dst.cursor()
            psycopg2.extras.execute_batch(dst_cursor, insert_sql, rows)
            dst.commit()
            print(f"  [{table}] {len(rows)} rows in source, migrate pass complete")

        print("\nMigration complete. SQLite source file was not modified.")
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    migrate()
