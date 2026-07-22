from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String

from app.database import Base


class User(Base):
    """
    A registered operator of the platform.

    The password is never stored — only a bcrypt hash, which is a one-way
    function with a tunable work factor.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)

    # Authoritative role. The client cannot influence this: it is read from the
    # database on every request via the session token.
    role = Column(String(32), nullable=False, default="engineer")

    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)


class UserSession(Base):
    """
    A server-side login session.

    Opaque random tokens are used rather than JWTs so that logout genuinely
    invalidates access: the row is deleted and the token stops working
    immediately. A stateless JWT would remain valid until it expired.

    Only a SHA-256 hash of the token is stored, so a database leak does not
    hand an attacker usable session tokens.
    """

    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    user_agent = Column(String(255), nullable=True)


Index("ix_user_sessions_expiry", UserSession.expires_at)
