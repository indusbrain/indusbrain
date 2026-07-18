from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.database import Base

class ChatMessage(Base):
    """
    Production Relational Ledger. Securely stores historical dialogue parameters 
    directly on hard disk storage to protect context records across reboots.
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), index=True, nullable=False)
    sender = Column(String(50), nullable=False)  # Explicit tags: 'operator' or 'agent'
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)