"""
Conversation management: list, rename, delete and search chat threads.

Ownership
---------
A thread belongs to an `owner_key`:
  - secure mode : "user:<id>"        (the signed-in account)
  - demo mode   : "client:<uuid>"    (a per-browser id sent by the frontend)

A caller only ever sees their own threads, in either mode.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user_optional
from app.database import get_db
from app.models.chat_history import ChatMessage
from app.models.conversation import Conversation
from app.models.user import User

router = APIRouter(prefix="/conversations", tags=["Conversation History"])

CLIENT_HEADER = "X-IndusBrain-Client"


def resolve_owner_key(user: Optional[User], client_id: str) -> str:
    """A signed-in account always takes precedence over a browser-supplied id."""
    if user is not None:
        return f"user:{user.id}"
    return f"client:{(client_id or 'anonymous').strip()[:180]}"


async def owner_key_dependency(
    user: Optional[User] = Depends(get_current_user_optional),
    client_id: str = Header(default="anonymous", alias=CLIENT_HEADER),
) -> str:
    return resolve_owner_key(user, client_id)


def derive_title(first_question: str) -> str:
    """Builds a readable thread title from the opening question."""
    cleaned = " ".join(first_question.strip().split())
    if len(cleaned) <= 60:
        return cleaned or "New conversation"
    return cleaned[:57].rstrip() + "…"


async def ensure_conversation(
    db: AsyncSession, session_id: str, owner_key: str, first_question: str
) -> Conversation:
    """Fetches the thread for a session, creating it on the first message."""
    result = await db.execute(select(Conversation).where(Conversation.session_id == session_id))
    conversation = result.scalars().first()

    if conversation is None:
        conversation = Conversation(
            session_id=session_id,
            owner_key=owner_key,
            title=derive_title(first_question),
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)

    return conversation


async def touch_conversation(db: AsyncSession, session_id: str, preview: str) -> None:
    """Updates the thread's activity timestamp, message count and preview."""
    result = await db.execute(select(Conversation).where(Conversation.session_id == session_id))
    conversation = result.scalars().first()
    if conversation is None:
        return

    count_result = await db.execute(
        select(func.count(ChatMessage.id)).where(ChatMessage.session_id == session_id)
    )
    conversation.message_count = count_result.scalar() or 0
    conversation.last_preview = " ".join((preview or "").split())[:280]
    await db.commit()


class ConversationSummary(BaseModel):
    id: int
    session_id: str
    title: str
    message_count: int
    last_preview: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RenameRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)


@router.get("", response_model=List[ConversationSummary])
async def list_conversations(
    search: str = Query(default="", description="Filter by title or message content."),
    limit: int = Query(default=50, le=200),
    owner_key: str = Depends(owner_key_dependency),
    db: AsyncSession = Depends(get_db),
):
    """Lists the caller's threads, most recently active first."""
    statement = select(Conversation).where(Conversation.owner_key == owner_key)

    term = search.strip()
    if term:
        # Search titles AND message bodies, so a thread is findable by something
        # said inside it rather than only by its title.
        matching_sessions = select(ChatMessage.session_id).where(
            ChatMessage.content.ilike(f"%{term}%")
        )
        statement = statement.where(
            or_(
                Conversation.title.ilike(f"%{term}%"),
                Conversation.session_id.in_(matching_sessions),
            )
        )

    statement = statement.order_by(Conversation.updated_at.desc()).limit(limit)
    conversations = (await db.execute(statement)).scalars().all()

    return [
        ConversationSummary(
            id=c.id,
            session_id=c.session_id,
            title=c.title,
            message_count=c.message_count,
            last_preview=c.last_preview,
            created_at=c.created_at.isoformat() if c.created_at else None,
            updated_at=c.updated_at.isoformat() if c.updated_at else None,
        )
        for c in conversations
    ]


@router.patch("/{session_id}", response_model=ConversationSummary)
async def rename_conversation(
    session_id: str,
    payload: RenameRequest,
    owner_key: str = Depends(owner_key_dependency),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(
            Conversation.session_id == session_id, Conversation.owner_key == owner_key
        )
    )
    conversation = result.scalars().first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    conversation.title = payload.title.strip()[:200]
    await db.commit()
    await db.refresh(conversation)

    return ConversationSummary(
        id=conversation.id,
        session_id=conversation.session_id,
        title=conversation.title,
        message_count=conversation.message_count,
        last_preview=conversation.last_preview,
        created_at=conversation.created_at.isoformat() if conversation.created_at else None,
        updated_at=conversation.updated_at.isoformat() if conversation.updated_at else None,
    )


@router.delete("/{session_id}", status_code=status.HTTP_200_OK)
async def delete_conversation(
    session_id: str,
    owner_key: str = Depends(owner_key_dependency),
    db: AsyncSession = Depends(get_db),
):
    """Deletes a thread and every message in it."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.session_id == session_id, Conversation.owner_key == owner_key
        )
    )
    conversation = result.scalars().first()
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")

    await db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
    await db.execute(delete(Conversation).where(Conversation.id == conversation.id))
    await db.commit()

    return {"status": "DELETED", "session_id": session_id}
