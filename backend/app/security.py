"""
Role-based access control.

The role is now read from the AUTHENTICATED USER's database record. It was
previously taken from a request header, which meant any caller could claim any
role — authorization without authentication. Both halves are now real:

  - Identity  : a bcrypt-verified login issuing a revocable session token
  - Authority : permissions looked up from the user's stored role

A permission check therefore cannot be bypassed by editing a header.
"""

import os
from enum import Enum
from typing import Dict, List, Optional, Set

from fastapi import Depends, Header, HTTPException, status

from app.auth import get_current_user_optional
from app.models.user import User

# ---------------------------------------------------------------------------
# AUTH MODE
#
#   demo   - no sign-in. The role is chosen in the UI and sent as a header.
#            Permissions are still enforced per role, but identity is NOT
#            verified: any caller can claim any role. Intended for demos.
#
#   secure - full authentication. Sign-in required, role read from the user's
#            database record, header ignored.
#
# The secure path is fully implemented and tested; this flag only selects which
# one is active, so switching is a one-line config change.
# ---------------------------------------------------------------------------
AUTH_MODE = os.getenv("AUTH_MODE", "demo").strip().lower()
DEMO_MODE = AUTH_MODE != "secure"

ROLE_HEADER = "X-IndusBrain-Role"


class Role(str, Enum):
    ENGINEER = "engineer"
    MANAGER = "manager"


class Permission(str, Enum):
    # Read
    VIEW_DASHBOARD = "view_dashboard"
    VIEW_KNOWLEDGE = "view_knowledge"
    VIEW_CONFLICTS = "view_conflicts"
    VIEW_ANALYTICS = "view_analytics"
    # Interact
    ASK_QUESTIONS = "ask_questions"
    RUN_SIMULATION = "run_simulation"
    SCAN_CONFLICTS = "scan_conflicts"
    VIEW_DOCUMENTS = "view_documents"
    DOWNLOAD_DOCUMENTS = "download_documents"
    # Write / administrative
    UPLOAD_DOCUMENTS = "upload_documents"
    DELETE_DOCUMENTS = "delete_documents"
    REPLACE_DOCUMENTS = "replace_documents"
    REBUILD_INDEX = "rebuild_index"


# An engineer can do everything needed to answer an operational question, but
# cannot change the shared corpus.
#
# Deliberately granted to engineers: conflicts and analytics. An engineer
# diagnosing a fault must know that a specification is contradicted or that an
# asset is undocumented. Withholding that would make the tool less safe, which is
# the opposite of this product's purpose.
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ENGINEER: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_KNOWLEDGE,
        Permission.VIEW_CONFLICTS,
        Permission.VIEW_ANALYTICS,
        Permission.ASK_QUESTIONS,
        Permission.RUN_SIMULATION,
        Permission.SCAN_CONFLICTS,
        Permission.VIEW_DOCUMENTS,
        Permission.DOWNLOAD_DOCUMENTS,
    },
    Role.MANAGER: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_KNOWLEDGE,
        Permission.VIEW_CONFLICTS,
        Permission.VIEW_ANALYTICS,
        Permission.ASK_QUESTIONS,
        Permission.RUN_SIMULATION,
        Permission.SCAN_CONFLICTS,
        Permission.VIEW_DOCUMENTS,
        Permission.DOWNLOAD_DOCUMENTS,
        Permission.UPLOAD_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
        Permission.REPLACE_DOCUMENTS,
        Permission.REBUILD_INDEX,
    },
}

ROLE_DESCRIPTIONS: Dict[Role, str] = {
    Role.ENGINEER: (
        "Plant and maintenance engineers. Full read and query access to the "
        "knowledge base, including conflicts and analytics. Cannot alter the "
        "shared document corpus."
    ),
    Role.MANAGER: (
        "Knowledge managers and supervisors. Everything an engineer can do, plus "
        "curating the corpus: uploading, replacing and removing documents, and "
        "rebuilding the knowledge graph."
    ),
}


def coerce_role(value) -> Role:
    """
    Normalises a stored role string into a Role.

    NOTE: Role subclasses str, so `str(Role.MANAGER)` yields 'Role.MANAGER', not
    'manager'. Enum instances must be handled first or they fail to parse and
    silently downgrade to the default role.
    """
    if isinstance(value, Role):
        return value
    try:
        return Role(str(value).strip().lower())
    except ValueError:
        return Role.ENGINEER


def permissions_for(role: Role) -> List[str]:
    return sorted(p.value for p in ROLE_PERMISSIONS.get(role, set()))


def user_can(user: User, permission: Permission) -> bool:
    return permission in ROLE_PERMISSIONS.get(coerce_role(user.role), set())


def require(permission: Permission):
    """
    FastAPI dependency factory enforcing a permission.

    In SECURE mode: 401 when nobody is signed in, 403 when the signed-in user's
    role lacks the permission — distinct codes so the client can tell "log in"
    apart from "you are not allowed".

    In DEMO mode: the role comes from the request header (defaulting to the
    least-privileged role). Permissions are still enforced, so an engineer still
    receives 403 on an upload — but identity is not verified.
    """

    async def guard(
        user: Optional[User] = Depends(get_current_user_optional),
        role_header: str = Header(default=Role.ENGINEER.value, alias=ROLE_HEADER),
    ) -> Optional[User]:
        # A real session always wins, even in demo mode, so a signed-in user
        # cannot escalate by sending a header.
        if user is not None:
            effective_role = coerce_role(user.role)
        elif DEMO_MODE:
            effective_role = coerce_role(role_header)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sign in to continue.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if permission not in ROLE_PERMISSIONS.get(effective_role, set()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"The {effective_role.value} role is not permitted to "
                    f"{permission.value.replace('_', ' ')}."
                ),
            )
        return user

    return guard
