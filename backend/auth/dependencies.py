"""Reusable FastAPI dependencies for protected routes.

get_current_user is the one abstraction every protected router depends on:
read the session cookie, hash it, look the hash up, and walk through every
reason the session could be invalid before resolving a user. Nothing here
ever trusts a user id supplied by the client — the session cookie (opaque,
HttpOnly) is the only source of identity.
"""

from datetime import datetime, timezone

from fastapi import Cookie, Header, HTTPException, Request, status

import memory.database as db
from auth.security import SESSION_COOKIE_NAME, hash_token


def _parse_db_timestamp(value) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    # SQLite stores TIMESTAMP as text. Two shapes reach here: SQL-side
    # CURRENT_TIMESTAMP ("YYYY-MM-DD HH:MM:SS", implicitly UTC) and Python's
    # sqlite3 adapter for a timezone-aware datetime (ISO 8601 with offset,
    # e.g. "...+00:00") — session_expiry() produces the latter.
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    raise ValueError(f"unrecognized timestamp format: {value!r}")


_UNAUTHENTICATED = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


async def get_current_user(
    request: Request,
    session_cookie: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
) -> dict:
    if not session_cookie:
        raise _UNAUTHENTICATED

    token_hash = hash_token(session_cookie)
    session = db.get_session_by_token_hash(token_hash)
    if session is None:
        raise _UNAUTHENTICATED
    if session["revoked_at"] is not None:
        raise _UNAUTHENTICATED
    if _parse_db_timestamp(session["expires_at"]) <= datetime.now(timezone.utc):
        raise _UNAUTHENTICATED

    user = db.get_user_by_id(session["user_id"])
    if user is None or not user["is_active"]:
        raise _UNAUTHENTICATED

    db.touch_session(session["id"])
    request.state.user = user
    request.state.session_token = session_cookie
    return user


def verify_csrf_header(x_rinti_client: str | None = Header(default=None)) -> None:
    """Lightweight CSRF defense for state-changing requests.

    The session cookie is HttpOnly (unreadable by JS), so the classic
    double-submit-cookie pattern doesn't apply here. Instead this relies on a
    combination that's standard for same-origin SPA+cookie APIs:
      1. SameSite=Lax on the session cookie — the browser won't attach it to
         a cross-site POST/PUT/PATCH/DELETE in the first place.
      2. This header — a plain cross-site HTML form cannot set a custom
         request header, so its absence flags exactly the request shape a
         forged form submission would produce.
      3. A strict CORS allowlist (see main.py) — a cross-origin fetch/XHR
         that *does* set this header still has to pass a CORS preflight the
         browser enforces against our explicit origin list.
    None of the three alone is a complete CSRF story; together they cover the
    practical surface without adding infrastructure (no CSRF-token table/cache).
    """
    if x_rinti_client != "1":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing required client header")
