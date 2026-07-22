from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database import Base


class Conversation(Base):
    """
    A named chat thread.

    Chat turns were previously stored against a bare session id with no thread
    record, so there was nothing to list, title, rename or delete. This is the
    parent every message now hangs off.

    `owner_key` identifies who the thread belongs to. In secure mode that is the
    user id; in demo mode it is the browser's local client id. Either way a
    thread is only ever listed back to its own owner.
    """

    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    owner_key = Column(String(255), nullable=False, index=True)

    # Derived from the first question asked, so threads are recognisable in a list.
    title = Column(String(200), nullable=False, default="New conversation")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    message_count = Column(Integer, nullable=False, default=0)

    # Snippet of the most recent answer, for the conversation list preview.
    last_preview = Column(Text, nullable=True)
