"""Registration, login, logout, and session restoration.

Every response here is the "safe" user shape only (id/name/email/timestamps) —
password_hash never leaves database.py, and the raw session token is never
echoed back in a JSON body, only set as an HttpOnly cookie.
"""

import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, field_validator

import memory.database as db
from auth.dependencies import get_current_user, verify_csrf_header
from auth.security import (
    SESSION_COOKIE_NAME,
    cookie_kwargs,
    generate_session_token,
    hash_password,
    hash_token,
    is_valid_email,
    is_valid_name,
    is_valid_password,
    normalize_email,
    session_expiry,
    verify_password,
)

router = APIRouter()

# A fixed, valid Argon2id hash of an unrelated placeholder password — verified
# against on every login attempt for a nonexistent account so lookup failure
# and password failure take the same time (mitigates timing-based user
# enumeration). Never a real user's hash.
_DUMMY_HASH = hash_password("not-a-real-password-used-only-for-timing-parity")


# ── request/response models ──

class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserProfile(BaseModel):
    id: str
    name: str
    email: str
    created_at: str
    updated_at: str | None = None


# ── lightweight brute-force protection ──
# In-memory, per-process — adequate for a single-instance SQLite deployment
# (documented limitation: does not share state across multiple app processes).
# Keyed by normalized email so a flood of failures against one account is
# throttled without ever confirming whether that account exists.
_FAILED_LOGIN_WINDOW_SECONDS = 300
_FAILED_LOGIN_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 30
_failed_attempts: Dict[str, Deque[float]] = defaultdict(deque)


def _check_login_throttle(email: str) -> None:
    now = time.monotonic()
    attempts = _failed_attempts[email]
    while attempts and now - attempts[0] > _FAILED_LOGIN_WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= _FAILED_LOGIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Please wait a moment and try again.",
        )


def _record_login_failure(email: str) -> None:
    _failed_attempts[email].append(time.monotonic())


def _clear_login_failures(email: str) -> None:
    _failed_attempts.pop(email, None)


def _issue_session(response: Response, user_id: str) -> None:
    token = generate_session_token()
    db.create_session(user_id, hash_token(token), session_expiry())
    response.set_cookie(SESSION_COOKIE_NAME, token, max_age=30 * 24 * 3600, **cookie_kwargs())


def _safe_profile(user: dict) -> UserProfile:
    return UserProfile(
        id=user["id"], name=user["name"], email=user["email"],
        created_at=user["created_at"], updated_at=user.get("updated_at"),
    )


# ── endpoints ──

@router.post("/auth/register", response_model=UserProfile, dependencies=[Depends(verify_csrf_header)])
async def register(payload: RegisterRequest, response: Response):
    name = payload.name.strip()
    email = normalize_email(payload.email)

    if not is_valid_name(name):
        raise HTTPException(status_code=400, detail="Please enter your name.")
    if not is_valid_email(email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    if not is_valid_password(payload.password):
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    if db.get_user_by_email(email) is not None:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = db.create_user(name, email, hash_password(payload.password))
    _issue_session(response, user["id"])
    return _safe_profile(user)


@router.post("/auth/login", response_model=UserProfile, dependencies=[Depends(verify_csrf_header)])
async def login(payload: LoginRequest, response: Response):
    email = normalize_email(payload.email)
    _check_login_throttle(email)

    user = db.get_user_by_email(email)
    # Verify against a real hash either way so a nonexistent account doesn't
    # respond measurably faster than a wrong-password one (timing-based
    # user enumeration). The dummy hash below is a fixed, valid Argon2id hash
    # of an unrelated placeholder — never a real user's hash.
    password_hash = user["password_hash"] if user else _DUMMY_HASH
    password_ok = verify_password(password_hash, payload.password)

    if user is None or not password_ok or not user["is_active"]:
        _record_login_failure(email)
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    _clear_login_failures(email)
    _issue_session(response, user["id"])
    return _safe_profile(user)


@router.post("/auth/logout", dependencies=[Depends(verify_csrf_header)])
async def logout(request: Request, response: Response):
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        db.revoke_session_by_token_hash(hash_token(token))
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"status": "logged_out"}


@router.get("/auth/me", response_model=UserProfile)
async def me(current_user: dict = Depends(get_current_user)):
    return _safe_profile(current_user)
