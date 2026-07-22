from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from app.database import Base


class ChatMessage(Base):
    """
    A single turn in a conversation.

    `evidence` stores the audit payload that accompanied an agent answer:
    citations, confidence breakdown, organizational memory and the decision
    trace.

    It is persisted rather than discarded because the previous implementation
    kept only the answer text. Reloading the page restored the words but lost
    every source — and provenance that disappears on refresh is not provenance.
    For an auditable industrial record it has to outlive the browser session.
    """

    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True, nullable=False)
    sender = Column(String(50), nullable=False)  # 'operator' or 'agent'
    content = Column(Text, nullable=False)
    evidence = Column(JSONB, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
