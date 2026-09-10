"""Password hashing, session tokens, and cookie policy for R1.6A auth.

Nothing here invents its own cryptography: password hashing is argon2-cffi's
PasswordHasher (Argon2id, library-chosen salt), session tokens are
`secrets.token_urlsafe`, and only a SHA-256 hash of the token is ever stored —
the raw token exists only in the HttpOnly cookie on the browser and in the
response the moment it is issued.
"""

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

from config import settings

_hasher = PasswordHasher()  # library defaults: Argon2id, tuned for interactive login

SESSION_TOKEN_BYTES = 32
SESSION_TTL_DAYS = 30

# __Host- requires Secure (HTTPS) and no Domain attribute; only usable once the
# app is actually served over TLS. In local dev the backend/frontend split
# across localhost:3000 <-> 127.0.0.1:8000 is plain HTTP, so Secure cookies
# would simply be refused by the browser — the flags below track environment
# rather than being hardcoded, so the same code is correct in both.
IS_PRODUCTION = settings.environment == "production"
SESSION_COOKIE_NAME = "__Host-rinti_session" if IS_PRODUCTION else "rinti_session"

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email)) and len(email) <= 254


def is_valid_password(password: str) -> bool:
    return isinstance(password, str) and 8 <= len(password) <= 256


def is_valid_name(name: str) -> bool:
    return isinstance(name, str) and 1 <= len(name.strip()) <= 100


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        _hasher.verify(password_hash, password)
        return True
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def generate_session_token() -> str:
    """The raw, high-entropy token. Sent to the browser once, never stored."""
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def hash_token(token: str) -> str:
    """What actually lives in the sessions table — a lookup key, not a secret."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def session_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def cookie_kwargs() -> dict:
    """Flags applied to the session cookie on both set and clear.

    SameSite=Lax + HttpOnly + a strict CORS allowlist together cover the
    practical CSRF surface for this same-origin architecture; see
    auth/dependencies.py:verify_csrf_header for the additional header check
    applied to state-changing requests.
    """
    return {
        "httponly": True,
        "secure": IS_PRODUCTION,
        "samesite": "lax",
        "path": "/",
    }
