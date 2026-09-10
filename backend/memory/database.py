import sqlite3
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from config import settings

# Deterministic id for the account existing (pre-auth) local data is migrated
# to. Fixed rather than randomly generated so re-running init_db() never
# creates a second one and the assignment is reproducible across restarts.
LEGACY_DATA_OWNER_ID = "00000000-0000-0000-0000-000000000001"
LEGACY_DATA_OWNER_EMAIL = "dev@rinti.local"
LEGACY_DATA_OWNER_NAME = "Rinti Dev"
# Local-only placeholder credential for the migrated dev account — documented
# here rather than hidden, since this path only exists to keep pre-auth
# development data reachable instead of orphaning or deleting it.
LEGACY_DATA_OWNER_PASSWORD = "rinti-dev-local-only"

def get_connection():
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def _column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cursor.fetchall())

def init_db():
    """Initializes the SQLite schema for conversations, settings, and persistent memory.

    Safe to call on every startup: existing tables/rows/columns are left untouched
    (CREATE TABLE IF NOT EXISTS + column-existence checks before any ALTER TABLE).
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Conversations
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Conversation Messages
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            role TEXT,
            content TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        )
    ''')

    # 3. Settings (Single row)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            tts_enabled BOOLEAN DEFAULT 1,
            wake_word_enabled BOOLEAN DEFAULT 0,
            memory_enabled BOOLEAN DEFAULT 1,
            voice_id TEXT DEFAULT 'alloy'
        )
    ''')
    cursor.execute('INSERT OR IGNORE INTO settings (id) VALUES (1)')

    # 4. Persistent Memory (Facts, preferences, project context)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            category TEXT DEFAULT 'general',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 5. Research sessions (R1.5). Structured detail is kept as JSON for now; it can be
    #    normalized into research_sources/claims/evidence tables in a later phase.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS research_sessions (
            id TEXT PRIMARY KEY,
            conversation_id TEXT,
            query TEXT NOT NULL,
            mode TEXT DEFAULT 'QUICK',
            intent TEXT,
            status TEXT DEFAULT 'completed',
            partial BOOLEAN DEFAULT 0,
            result_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(conversation_id) REFERENCES conversations(id)
        )
    ''')
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_research_sessions_conversation "
        "ON research_sessions(conversation_id)"
    )

    # 6. Safe migrations for databases created before these columns existed
    if not _column_exists(cursor, "conversations", "title"):
        cursor.execute("ALTER TABLE conversations ADD COLUMN title TEXT")
    if not _column_exists(cursor, "conversations", "updated_at"):
        cursor.execute("ALTER TABLE conversations ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    if not _column_exists(cursor, "memories", "enabled"):
        cursor.execute("ALTER TABLE memories ADD COLUMN enabled BOOLEAN DEFAULT 1")
    if not _column_exists(cursor, "messages", "research_session_id"):
        cursor.execute("ALTER TABLE messages ADD COLUMN research_session_id TEXT")

    # 7. Users + sessions (R1.6A). SQLite can't retrofit a FOREIGN KEY onto an
    #    existing table via ALTER TABLE, so referential integrity for user_id
    #    on the pre-existing conversations/memories/research_sessions tables
    #    is enforced at the application layer (every query below filters by
    #    the authenticated user's id); it's a real FK constraint here because
    #    these are new tables created with it from the start.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            revoked_at TIMESTAMP,
            last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token_hash ON sessions(token_hash)")

    # 7b. Per-user daily usage counters (chat messages / research queries).
    # One row per (user, UTC date) — the app-enforced fair-share limit that
    # sits on top of the one shared, server-side Groq/Tavily account, so one
    # user's usage never counts against another user's own daily allowance.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_daily (
            user_id TEXT NOT NULL,
            usage_date TEXT NOT NULL,
            chat_count INTEGER NOT NULL DEFAULT 0,
            research_count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, usage_date),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')

    # 8. user_id ownership columns on pre-existing tables.
    if not _column_exists(cursor, "conversations", "user_id"):
        cursor.execute("ALTER TABLE conversations ADD COLUMN user_id TEXT")
    if not _column_exists(cursor, "memories", "user_id"):
        cursor.execute("ALTER TABLE memories ADD COLUMN user_id TEXT")
    if not _column_exists(cursor, "research_sessions", "user_id"):
        cursor.execute("ALTER TABLE research_sessions ADD COLUMN user_id TEXT")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_user ON memories(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_research_sessions_user ON research_sessions(user_id)")

    # 9. Migrate any pre-auth data (user_id IS NULL) to a deterministic local
    #    dev account instead of leaving it orphaned or deleting it. Only runs
    #    once in practice — after the first backfill every row has a user_id.
    cursor.execute(
        "SELECT COUNT(*) FROM conversations WHERE user_id IS NULL "
        "UNION ALL SELECT COUNT(*) FROM memories WHERE user_id IS NULL "
        "UNION ALL SELECT COUNT(*) FROM research_sessions WHERE user_id IS NULL"
    )
    orphaned_counts = [row[0] for row in cursor.fetchall()]
    if any(orphaned_counts):
        cursor.execute("SELECT id FROM users WHERE id = ?", (LEGACY_DATA_OWNER_ID,))
        if not cursor.fetchone():
            # Imported lazily: auth.security only depends on config, but this
            # keeps memory.database importable even before argon2 is installed.
            from auth.security import hash_password

            cursor.execute(
                "INSERT INTO users (id, name, email, password_hash, is_active) VALUES (?, ?, ?, ?, 1)",
                (
                    LEGACY_DATA_OWNER_ID,
                    LEGACY_DATA_OWNER_NAME,
                    LEGACY_DATA_OWNER_EMAIL,
                    hash_password(LEGACY_DATA_OWNER_PASSWORD),
                ),
            )
        cursor.execute(
            "UPDATE conversations SET user_id = ? WHERE user_id IS NULL", (LEGACY_DATA_OWNER_ID,)
        )
        cursor.execute(
            "UPDATE memories SET user_id = ? WHERE user_id IS NULL", (LEGACY_DATA_OWNER_ID,)
        )
        cursor.execute(
            "UPDATE research_sessions SET user_id = ? WHERE user_id IS NULL", (LEGACY_DATA_OWNER_ID,)
        )

    conn.commit()
    conn.close()

# ── User Functions ──

def create_user(name: str, email: str, password_hash: str) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    user_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO users (id, name, email, password_hash, is_active) VALUES (?, ?, ?, ?, 1)",
        (user_id, name, email, password_hash),
    )
    conn.commit()
    cursor.execute(
        "SELECT id, name, email, created_at, updated_at, is_active FROM users WHERE id = ?", (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row)

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, email, password_hash, created_at, updated_at, is_active FROM users WHERE email = ?",
        (email,),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, email, created_at, updated_at, is_active FROM users WHERE id = ?", (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# ── Session Functions ──

def create_session(user_id: str, token_hash: str, expires_at) -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    session_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO sessions (id, user_id, token_hash, expires_at) VALUES (?, ?, ?, ?)",
        (session_id, user_id, token_hash, expires_at),
    )
    conn.commit()
    conn.close()
    return {"id": session_id, "user_id": user_id}

def get_session_by_token_hash(token_hash: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, token_hash, created_at, expires_at, revoked_at, last_seen_at "
        "FROM sessions WHERE token_hash = ?",
        (token_hash,),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def touch_session(session_id: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET last_seen_at = CURRENT_TIMESTAMP WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

def revoke_session_by_token_hash(token_hash: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE sessions SET revoked_at = CURRENT_TIMESTAMP WHERE token_hash = ? AND revoked_at IS NULL",
        (token_hash,),
    )
    revoked = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return revoked

# ── Per-user daily usage (chat / research fair-share limits) ──

def check_and_increment_usage(user_id: str, kind: str, daily_limit: int) -> Dict[str, Any]:
    """Atomically checks then increments today's counter for this user.

    `kind` is "chat" or "research" — each has its own counter and limit,
    since a research call costs far more provider tokens than a chat message.
    Returns {"allowed", "used", "limit", "remaining"}. When not allowed, the
    counter is left untouched — a rejected request doesn't cost the user part
    of tomorrow's allowance.
    """
    if kind not in ("chat", "research"):
        raise ValueError(f"unknown usage kind: {kind!r}")
    column = f"{kind}_count"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO usage_daily (user_id, usage_date) VALUES (?, ?)",
        (user_id, today),
    )
    cursor.execute(
        f"SELECT {column} FROM usage_daily WHERE user_id = ? AND usage_date = ?",
        (user_id, today),
    )
    used = cursor.fetchone()[0]

    if used >= daily_limit:
        conn.commit()
        conn.close()
        return {"allowed": False, "used": used, "limit": daily_limit, "remaining": 0}

    cursor.execute(
        f"UPDATE usage_daily SET {column} = {column} + 1 WHERE user_id = ? AND usage_date = ?",
        (user_id, today),
    )
    conn.commit()
    conn.close()
    used += 1
    return {"allowed": True, "used": used, "limit": daily_limit, "remaining": daily_limit - used}


def get_usage_today(user_id: str) -> Dict[str, Any]:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT chat_count, research_count FROM usage_daily WHERE user_id = ? AND usage_date = ?",
        (user_id, today),
    )
    row = cursor.fetchone()
    conn.close()
    return {"chat_used": row["chat_count"] if row else 0, "research_used": row["research_count"] if row else 0}

# ── Conversation Functions (all scoped to the owning user) ──

def create_conversation(user_id: str) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    conv_id = str(uuid.uuid4())
    cursor.execute("INSERT INTO conversations (id, user_id) VALUES (?, ?)", (conv_id, user_id))
    conn.commit()
    conn.close()
    return conv_id

def conversation_owner(conversation_id: str) -> Optional[str]:
    """Returns the owning user_id, or None if the conversation doesn't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM conversations WHERE id = ?", (conversation_id,))
    row = cursor.fetchone()
    conn.close()
    return row["user_id"] if row else None

def save_message(conversation_id: str, role: str, content: str, research_session_id: Optional[str] = None):
    """Appends a message to a conversation the caller has already verified ownership of."""
    conn = get_connection()
    cursor = conn.cursor()
    msg_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO messages (id, conversation_id, role, content, research_session_id) VALUES (?, ?, ?, ?, ?)",
        (msg_id, conversation_id, role, content, research_session_id)
    )
    cursor.execute(
        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (conversation_id,)
    )
    conn.commit()
    conn.close()

def list_conversations(user_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, created_at, updated_at FROM conversations "
        "WHERE user_id = ? ORDER BY updated_at DESC, created_at DESC",
        (user_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_conversation_summary(conversation_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, created_at, updated_at FROM conversations WHERE id = ? AND user_id = ?",
        (conversation_id, user_id)
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def rename_conversation(conversation_id: str, user_id: str, title: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id)
    )
    if not cursor.fetchone():
        conn.close()
        return False
    cursor.execute(
        "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (title, conversation_id)
    )
    conn.commit()
    conn.close()
    return True

def delete_conversation(conversation_id: str, user_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id)
    )
    if not cursor.fetchone():
        conn.close()
        return False
    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    cursor.execute("DELETE FROM research_sessions WHERE conversation_id = ?", (conversation_id,))
    cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    conn.commit()
    conn.close()
    return True

def get_conversation_history(conversation_id: str, user_id: str, limit: int = 20) -> List[Dict]:
    """Returns [] both when the conversation doesn't exist and when it isn't
    owned by user_id — messages are only ever reachable through an owned
    conversation, and the two cases must look identical to the caller."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id)
    )
    if not cursor.fetchone():
        conn.close()
        return []
    cursor.execute(
        "SELECT id, role, content, timestamp, research_session_id FROM messages "
        "WHERE conversation_id = ? ORDER BY timestamp ASC LIMIT ?",
        (conversation_id, limit)
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "id": row["id"],
            "role": row["role"],
            "content": row["content"],
            "timestamp": row["timestamp"],
            "research_session_id": row["research_session_id"],
        }
        for row in rows
    ]

# ── Settings Functions ──

def get_settings() -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT tts_enabled, wake_word_enabled, memory_enabled, voice_id FROM settings WHERE id = 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row)

def update_settings(updates: Dict[str, Any]) -> Dict[str, Any]:
    if not updates:
        return get_settings()
        
    conn = get_connection()
    cursor = conn.cursor()
    fields = []
    values = []
    for key, value in updates.items():
        fields.append(f"{key} = ?")
        values.append(int(value) if isinstance(value, bool) else value)
        
    query = f"UPDATE settings SET {', '.join(fields)} WHERE id = 1"
    cursor.execute(query, values)
    conn.commit()
    conn.close()
    return get_settings()

# ── Persistent Memory Functions (all scoped to the owning user) ──

def get_all_memories(user_id: str, category: Optional[str] = None, enabled_only: bool = False) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT id, content, category, enabled, created_at FROM memories"
    conditions = ["user_id = ?"]
    params: List[Any] = [user_id]
    if category:
        conditions.append("category = ?")
        params.append(category)
    if enabled_only:
        conditions.append("enabled = 1")
    query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_memory(user_id: str, content: str, category: str = "general") -> Dict[str, Any]:
    conn = get_connection()
    cursor = conn.cursor()
    mem_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO memories (id, content, category, user_id) VALUES (?, ?, ?, ?)",
        (mem_id, content, category, user_id)
    )
    conn.commit()
    cursor.execute("SELECT id, content, category, enabled, created_at FROM memories WHERE id = ?", (mem_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row)

def update_memory(memory_id: str, user_id: str, content: Optional[str] = None, category: Optional[str] = None) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM memories WHERE id = ? AND user_id = ?", (memory_id, user_id))
    if not cursor.fetchone():
        conn.close()
        return None

    fields = []
    values: List[Any] = []
    if content is not None:
        fields.append("content = ?")
        values.append(content)
    if category is not None:
        fields.append("category = ?")
        values.append(category)

    if fields:
        values.append(memory_id)
        cursor.execute(f"UPDATE memories SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()

    cursor.execute("SELECT id, content, category, enabled, created_at FROM memories WHERE id = ?", (memory_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def set_memory_enabled(memory_id: str, user_id: str, enabled: bool) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM memories WHERE id = ? AND user_id = ?", (memory_id, user_id))
    if not cursor.fetchone():
        conn.close()
        return None

    cursor.execute("UPDATE memories SET enabled = ? WHERE id = ?", (1 if enabled else 0, memory_id))
    conn.commit()
    cursor.execute("SELECT id, content, category, enabled, created_at FROM memories WHERE id = ?", (memory_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row)

def delete_memory(memory_id: str, user_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM memories WHERE id = ? AND user_id = ?", (memory_id, user_id))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted