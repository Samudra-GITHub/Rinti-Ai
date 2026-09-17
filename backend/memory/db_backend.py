"""Dual SQLite/Postgres connection layer.

Every function in memory/database.py and research/storage.py was written
against sqlite3's interface: `get_connection()` returns something with
`.cursor()`, `conn.commit()`, `conn.close()`; cursors support
`.execute(sql, params)` with `?` placeholders, `.fetchone()`/`.fetchall()`
returning rows addressable by column name, and `.rowcount`.

Rather than rewrite every call site for a second dialect, this module gives
Postgres a connection/cursor pair that speaks the exact same interface, and
translates the handful of SQLite-specific SQL fragments the app actually
uses (`?` placeholders, `PRAGMA foreign_keys`, `PRAGMA table_info`,
`INSERT OR IGNORE`, `BOOLEAN` columns) into their Postgres equivalents at
execute() time. Application code (database.py, storage.py) never needs to
know which database it's talking to.

Selection is automatic: DATABASE_URL set -> Postgres (production). Unset ->
SQLite at settings.db_path (local dev, unchanged from before this module
existed).
"""

import re
import sqlite3
from typing import Any, Optional, Sequence

from config import settings

IS_POSTGRES = bool(settings.database_url)

_pool = None  # lazily-created psycopg2 connection pool, reused across warm serverless invocations


def _get_pool():
    global _pool
    if _pool is None:
        try:
            import psycopg2.pool
        except ImportError as exc:
            raise RuntimeError(
                f"psycopg2 is not installed or cannot be imported, but DATABASE_URL is set "
                f"({settings.database_url[:20]}...). This usually means the requirements.txt "
                f"dependency wasn't installed during the Vercel build. Error: {exc}"
            ) from exc

        try:
            _pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=5,
                dsn=settings.database_url,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to create Postgres connection pool with DATABASE_URL. "
                f"This usually means the connection string is invalid, or Postgres is unreachable. "
                f"Error: {exc}"
            ) from exc
    return _pool


def _translate_sql(sql: str) -> Optional[str]:
    """Rewrites one SQLite-flavoured statement into Postgres SQL.

    Returns None for statements that should be silently skipped against
    Postgres (e.g. PRAGMA foreign_keys, which SQLite needs to turn on FK
    enforcement per-connection but Postgres always enforces).
    """
    stripped = sql.strip()
    upper = stripped.upper()

    if upper.startswith("PRAGMA FOREIGN_KEYS"):
        return None

    if upper.startswith("PRAGMA TABLE_INFO"):
        match = re.search(r"PRAGMA\s+TABLE_INFO\((\w+)\)", stripped, re.IGNORECASE)
        table = match.group(1)
        # Aliased to `name` so callers using row["name"] (the column PRAGMA
        # table_info uses) work unchanged against either dialect.
        return (
            "SELECT column_name AS name FROM information_schema.columns "
            f"WHERE table_name = '{table}'"
        )

    out = stripped

    if re.search(r"(?i)\bINSERT\s+OR\s+IGNORE\s+INTO\b", out):
        out = re.sub(r"(?i)\bINSERT\s+OR\s+IGNORE\s+INTO\b", "INSERT INTO", out)
        out = out.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"

    if upper.startswith("CREATE TABLE"):
        # SQLite has no real boolean type (BOOLEAN columns already just hold
        # 0/1 integers under the hood) — mapping to INTEGER on the Postgres
        # side keeps every existing 0/1 read/write in the app code correct
        # without touching it, and avoids Postgres's strict int->bool cast
        # rules on both DEFAULT clauses and bound parameters.
        out = re.sub(r"(?i)\bBOOLEAN\b", "INTEGER", out)

    # No SQL text in this codebase uses a literal `?` character as data (no
    # LIKE wildcards, no JSON blobs built via string formatting into the
    # query itself) — every `?` is a placeholder, so a blanket swap is safe.
    out = out.replace("?", "%s")
    return out


class _PGCursor:
    """Wraps a psycopg2 RealDictCursor so callers can keep using `?`-style
    SQL and sqlite3.Row-style `row["col"]` / `dict(row)` access unchanged."""

    def __init__(self, raw_cursor):
        self._cursor = raw_cursor

    def execute(self, sql: str, params: Sequence[Any] = ()):
        translated = _translate_sql(sql)
        if translated is None:
            return self
        self._cursor.execute(translated, tuple(params) if params else None)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount

    def close(self):
        self._cursor.close()


class _PGConnection:
    """Pooled Postgres connection with sqlite3.Connection's interface.

    `.close()` returns the underlying connection to the pool instead of
    tearing down the TCP connection, so repeated `get_connection()` /
    `conn.close()` pairs (the pattern every function in database.py and
    storage.py already uses) reuse connections across a warm serverless
    instance instead of reconnecting on every call.
    """

    def __init__(self, raw_conn, pool):
        self._conn = raw_conn
        self._pool = pool

    def cursor(self) -> _PGCursor:
        from psycopg2.extras import RealDictCursor

        return _PGCursor(self._conn.cursor(cursor_factory=RealDictCursor))

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._pool.putconn(self._conn)

    def execute(self, sql: str, params: Sequence[Any] = ()):
        # init_db() calls conn.cursor() before executing, so this isn't on
        # the hot path, but kept for parity with sqlite3.Connection.
        return self.cursor().execute(sql, params)


def get_connection():
    """Returns a connection: Postgres (pooled) if DATABASE_URL is set, else
    the existing local SQLite file. Same call-site contract either way."""
    if IS_POSTGRES:
        pool = _get_pool()
        raw_conn = pool.getconn()
        return _PGConnection(raw_conn, pool)

    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def health_check() -> dict:
    """Cheap connectivity probe for the /api/health endpoint."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        conn.close()
        return {"connected": True, "backend": "postgres" if IS_POSTGRES else "sqlite"}
    except Exception as exc:  # noqa: BLE001 - health check must never raise
        return {"connected": False, "backend": "postgres" if IS_POSTGRES else "sqlite", "error": str(exc)}


def close_pool():
    """Called on app shutdown so the process doesn't leak pooled connections."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
