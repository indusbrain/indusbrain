"""
Authentication: password hashing, session issuance, and request identification.

Design decisions
----------------
1. **bcrypt for passwords.** Adaptive work factor, salted per password, and
   purpose-built for the job. Plain SHA-256 would be far too fast to brute-force
   against.

2. **Opaque session tokens, not JWTs.** Logout must actually revoke access. A
   stateless JWT stays valid until expiry no matter what the server does, so
   "log out" would be a lie told by the client. Deleting a session row makes the
   token stop working immediately.

3. **Only a hash of the token is stored.** A database leak then yields no usable
   session tokens.

4. **The role comes from the database**, never from the request. The previous
   header-based role could be set to anything by the caller.
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User, UserSession

SESSION_LIFETIME_HOURS = int(os.getenv("SESSION_LIFETIME_HOURS", "12"))
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))

MIN_PASSWORD_LENGTH = 8


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)).decode()


def verify_password(plain_password: str, stored_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), stored_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def describe_password_problem(password: str) -> Optional[str]:
    """Returns a human-readable reason a password is unacceptable, or None."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if password.isdigit() or password.isalpha():
        return "Password must contain both letters and numbers."
    return None


# ---------------------------------------------------------------------------
# Session tokens
# ---------------------------------------------------------------------------
def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


async def issue_session(db: AsyncSession, user: User, user_agent: str = "") -> tuple[str, datetime]:
    """Creates a session and returns (raw_token, expiry). The raw token is shown once."""
    raw_token = secrets.token_urlsafe(48)
    expires_at = datetime.utcnow() + timedelta(hours=SESSION_LIFETIME_HOURS)

    db.add(
        UserSession(
            token_hash=_hash_token(raw_token),
            user_id=user.id,
            expires_at=expires_at,
            user_agent=(user_agent or "")[:255],
        )
    )
    user.last_login_at = datetime.utcnow()
    await db.commit()
    return raw_token, expires_at


async def revoke_session(db: AsyncSession, raw_token: str) -> bool:
    result = await db.execute(
        delete(UserSession).where(UserSession.token_hash == _hash_token(raw_token))
    )
    await db.commit()
    return result.rowcount > 0


async def purge_expired_sessions(db: AsyncSession) -> int:
    result = await db.execute(delete(UserSession).where(UserSession.expires_at < datetime.utcnow()))
    await db.commit()
    return result.rowcount


# ---------------------------------------------------------------------------
# Request identification
# ---------------------------------------------------------------------------
def _extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


async def get_current_user_optional(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Resolves the signed-in user, or None. Used where anonymous access is allowed."""
    raw_token = _extract_bearer(authorization)
    if not raw_token:
        return None

    result = await db.execute(
        select(UserSession).where(UserSession.token_hash == _hash_token(raw_token))
    )
    session_row = result.scalars().first()
    if not session_row:
        return None

    if session_row.expires_at < datetime.utcnow():
        await db.execute(delete(UserSession).where(UserSession.id == session_row.id))
        await db.commit()
        return None

    user_result = await db.execute(select(User).where(User.id == session_row.user_id))
    user = user_result.scalars().first()
    if not user or not user.is_active:
        return None
    return user


async def get_current_user(
    user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    """Requires an authenticated user. Raises 401 otherwise."""
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sign in to continue.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
