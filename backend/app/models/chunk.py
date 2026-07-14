from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class KnowledgeChunk(Base):
    """
    Relational database representation of a context-isolated document chunk.
    Acts as the target anchor database model for semantic mapping.
    """
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)  # Sequential order index tracking inside the parent document
    page_number = Column(Integer, nullable=False)  # Original source page tracking matrix
    content = Column(Text, nullable=False)          # Isolated context string text snippet
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Establish an explicit relational back-reference link directly to the primary document model
    document = relationship("KnowledgeDocument", back_populates="chunks")

# Force register the structural back-reference relationship inside the parent document schema layout
from app.models.document import KnowledgeDocument
KnowledgeDocument.chunks = relationship("KnowledgeChunk", order_by=KnowledgeChunk.chunk_index, back_populates="document", cascade="all, delete-orphan")