"""
Role-based access control.

SCOPE — read this before assuming more than it does
---------------------------------------------------
This module implements AUTHORIZATION (what a role is permitted to do), and that
part is real: permissions are enforced server-side and a forbidden call returns
HTTP 403 regardless of what the UI shows.

It does NOT implement AUTHENTICATION (proving you are who you claim to be).
The active role arrives in a request header and is taken at face value. Anyone
who can reach the API can select any role.

That limitation is stated plainly here, in the API responses, and in the UI,
because a role selector dressed up as a login screen would imply a security
guarantee this system does not provide. Adding real authentication means issuing
signed tokens from a verified identity source — a deliberate next step, not
something to imply we already have.
"""

from enum import Enum
from typing import Dict, List, Set

from fastapi import Header, HTTPException, status


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
    # Write / administrative
    UPLOAD_DOCUMENTS = "upload_documents"
    DELETE_DOCUMENTS = "delete_documents"
    REBUILD_INDEX = "rebuild_index"


# An engineer can do everything needed to answer an operational question, but
# cannot change the shared corpus. A manager additionally curates that corpus.
#
# Deliberately NOT restricted from the engineer: analytics and conflicts. An
# engineer diagnosing a fault needs to know a specification is contradicted or
# that an asset is undocumented. Hiding that would make the tool less safe, which
# is the opposite of the product's purpose.
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ENGINEER: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_KNOWLEDGE,
        Permission.VIEW_CONFLICTS,
        Permission.VIEW_ANALYTICS,
        Permission.ASK_QUESTIONS,
        Permission.RUN_SIMULATION,
        Permission.SCAN_CONFLICTS,
    },
    Role.MANAGER: {
        Permission.VIEW_DASHBOARD,
        Permission.VIEW_KNOWLEDGE,
        Permission.VIEW_CONFLICTS,
        Permission.VIEW_ANALYTICS,
        Permission.ASK_QUESTIONS,
        Permission.RUN_SIMULATION,
        Permission.SCAN_CONFLICTS,
        Permission.UPLOAD_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
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
        "curating the corpus: uploading documents, removing them, and rebuilding "
        "the knowledge graph."
    ),
}

ROLE_HEADER = "X-IndusBrain-Role"


def coerce_role(value) -> Role:
    """
    Normalises a header value (or an already-parsed enum) into a Role.

    NOTE: Role subclasses str, so `str(Role.MANAGER)` yields 'Role.MANAGER', not
    'manager'. Passing an enum member through the string branch therefore fails
    to parse and silently downgrades to the default role. Enum instances must be
    handled first.
    """
    if isinstance(value, Role):
        return value
    try:
        return Role(str(value).strip().lower())
    except ValueError:
        return Role.ENGINEER


def resolve_role(role_header: str = Header(default=Role.ENGINEER.value, alias=ROLE_HEADER)) -> Role:
    """
    Reads the active role from the request header.

    Defaults to the least-privileged role so a client that sends no header can
    never accidentally obtain write access.
    """
    return coerce_role(role_header)


def permissions_for(role: Role) -> List[str]:
    return sorted(p.value for p in ROLE_PERMISSIONS.get(role, set()))


def require(permission: Permission):
    """
    FastAPI dependency factory enforcing a single permission.

    Usage:
        @router.post("/upload", dependencies=[Depends(require(Permission.UPLOAD_DOCUMENTS))])
    """

    def guard(role: str = Header(default=Role.ENGINEER.value, alias=ROLE_HEADER)) -> Role:
        resolved = coerce_role(role)
        if permission not in ROLE_PERMISSIONS.get(resolved, set()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"The '{resolved.value}' role is not permitted to {permission.value.replace('_', ' ')}. "
                    f"Switch to a role that has this permission."
                ),
            )
        return resolved

    return guard
