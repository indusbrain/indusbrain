"""Registration, login, logout and identity endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    describe_password_problem,
    get_current_user,
    hash_password,
    issue_session,
    revoke_session,
    verify_password,
)
from app.database import get_db
from app.models.user import User
from app.security import ROLE_DESCRIPTIONS, Role, coerce_role, permissions_for

router = APIRouter(prefix="/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    password: str = Field(..., min_length=8)
    role: str = Field(default="engineer")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserProfile(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    role_description: str
    permissions: list[str]
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserProfile


def build_profile(user: User) -> UserProfile:
    role = coerce_role(user.role)
    return UserProfile(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=role.value,
        role_description=ROLE_DESCRIPTIONS[role],
        permissions=permissions_for(role),
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=AuthResponse)
async def register(
    payload: RegisterRequest,
    user_agent: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
):
    """
    Creates an account and signs the user straight in.

    The FIRST account created becomes a manager, so a fresh deployment has an
    administrator without needing a seeded password. Every later account defaults
    to engineer; managers are promoted deliberately rather than by self-selection.
    """
    email = payload.email.lower().strip()

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    problem = describe_password_problem(payload.password)
    if problem:
        raise HTTPException(status_code=422, detail=problem)

    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    assigned_role = Role.MANAGER if total_users == 0 else coerce_role(payload.role)

    # Self-registration cannot grant manager rights once the platform is set up.
    if total_users > 0 and assigned_role == Role.MANAGER:
        assigned_role = Role.ENGINEER

    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=assigned_role.value,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token, expires_at = await issue_session(db, user, user_agent)
    return AuthResponse(access_token=token, expires_at=expires_at, user=build_profile(user))


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    user_agent: str = Header(default=""),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == payload.email.lower().strip()))
    user = result.scalars().first()

    # Identical message and code whether the email is unknown or the password is
    # wrong, so the endpoint cannot be used to enumerate registered accounts.
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated.")

    token, expires_at = await issue_session(db, user, user_agent)
    return AuthResponse(access_token=token, expires_at=expires_at, user=build_profile(user))


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    authorization: Optional[str] = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Revokes the current session server-side, so the token stops working immediately."""
    if not authorization:
        return {"status": "NO_SESSION"}
    parts = authorization.split(None, 1)
    if len(parts) != 2:
        return {"status": "NO_SESSION"}

    revoked = await revoke_session(db, parts[1].strip())
    return {"status": "LOGGED_OUT" if revoked else "NO_SESSION"}


@router.get("/me", response_model=UserProfile)
async def current_profile(user: User = Depends(get_current_user)):
    return build_profile(user)


@router.get("/roles")
async def list_roles():
    """Role definitions, so the UI builds navigation from the server's permission table."""
    from app.security import DEMO_MODE

    return {
        "auth_mode": "demo" if DEMO_MODE else "secure",
        "authentication_implemented": not DEMO_MODE,
        "notice": (
            "Demo mode: roles are selected in the UI and enforced per role, but "
            "identity is not verified. Set AUTH_MODE=secure to require sign-in."
            if DEMO_MODE
            else None
        ),
        "roles": [
            {
                "id": role.value,
                "name": role.value.capitalize(),
                "description": ROLE_DESCRIPTIONS[role],
                "permissions": permissions_for(role),
            }
            for role in Role
        ],
    }


@router.get("/bootstrap")
async def bootstrap_state(db: AsyncSession = Depends(get_db)):
    """
    Tells the login screen whether any account exists yet, so a fresh deployment
    can present "create the first (manager) account" instead of a login form.
    """
    from app.security import DEMO_MODE

    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    return {
        "auth_mode": "demo" if DEMO_MODE else "secure",
        "requires_login": not DEMO_MODE,
        "has_users": total_users > 0,
        "user_count": total_users,
    }
