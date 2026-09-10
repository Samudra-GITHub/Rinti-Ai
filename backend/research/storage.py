"""Research session persistence.

Deliberately minimal for Phase 1: one table, with the structured result kept as
JSON so the shape can evolve before it is normalized into dedicated
research_sources / research_claims / research_evidence tables later (R1.5 §23/§45).
"""

import json
from typing import Any, Dict, List, Optional

import memory.database as db
from research.models import ResearchResult


def save_session(
    result: ResearchResult,
    *,
    conversation_id: Optional[str],
    user_id: str,
    status: str = "completed",
) -> None:
    conn = db.get_connection()
    cursor = conn.cursor()

    payload = {
        # Same shape the SSE "source" event sends the browser (source.to_public),
        # and the same 1-based numbering the engine assigns during the run — so a
        # rehydrated session renders identically to the live stream.
        "sources": [s.to_public(i + 1) for i, s in enumerate(result.sources)],
        "citations": [
            {"n": c.citation_number, "source_id": c.source_id, "claim_id": c.claim_id}
            for c in result.citations
        ],
        "notes": result.notes,
        "usage": result.usage.as_dict(),
        "answer": result.answer,
        # The structured presentation tree (R1.6B) — what the frontend renders
        # after a refresh. `answer` above stays the flattened text used for
        # conversation history / LLM follow-up context.
        "structured_answer": result.structured_answer.to_public() if result.structured_answer else None,
    }

    cursor.execute(
        """
        INSERT INTO research_sessions
            (id, conversation_id, user_id, query, mode, intent, status, partial, result_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            status = excluded.status,
            partial = excluded.partial,
            result_json = excluded.result_json,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            result.session_id,
            conversation_id,
            user_id,
            result.query,
            result.mode.value,
            result.intent.value,
            status,
            1 if result.partial else 0,
            json.dumps(payload, ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()


def get_session(session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
    """Returns None both when the session doesn't exist and when it belongs to
    another user — a session_id alone must never be enough to read it."""
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id, conversation_id, query, mode, intent, status, partial, result_json,
                  created_at, updated_at
           FROM research_sessions WHERE id = ? AND user_id = ?""",
        (session_id, user_id),
    )
    row = cursor.fetchone()
    conn.close()
    if row is None:
        return None

    data = dict(row)
    try:
        data["result"] = json.loads(data.pop("result_json") or "{}")
    except json.JSONDecodeError:
        data["result"] = {}
        data.pop("result_json", None)
    data["partial"] = bool(data.get("partial"))
    return data


def list_sessions_for_conversation(conversation_id: str, user_id: str) -> List[Dict[str, Any]]:
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT id, query, mode, intent, status, partial, created_at
           FROM research_sessions WHERE conversation_id = ? AND user_id = ?
           ORDER BY created_at DESC""",
        (conversation_id, user_id),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
