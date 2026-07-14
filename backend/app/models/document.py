import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Enum, BigInteger
from app.database import Base

class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PARSED = "parsed"
    EMBEDDED = "embedded"
    FAILED = "failed"

class KnowledgeDocument(Base):
    """
    Relational tracking ledger for all structural industrial knowledge assets 
    ingested into the IKIP enterprise workspace perimeter.
    """
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    s3_key = Column(String(512), unique=True, nullable=False, index=True)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(BigInteger, nullable=False) # Tracks data bounds in bytes
    status = Column(Enum(DocumentStatus), default=DocumentStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)