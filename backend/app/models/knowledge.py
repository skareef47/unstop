"""
KnowledgeDocument and KnowledgeChunk Models
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.models.base_types import VectorColumn
from app.core.config import settings


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    title = Column(String(255), nullable=False, index=True)
    source = Column(String(255), nullable=False)
    version = Column(String(50), nullable=False, default="1.0")
    status = Column(String(50), nullable=False, default="active", index=True)  # active, archived, draft
    content_hash = Column(String(64), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    document_id = Column(String(36), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    section = Column(String(255), nullable=False, default="General")
    chunk_metadata = Column(JSON, nullable=False, default=dict)
    embedding = Column(VectorColumn(settings.EMBEDDING_DIMENSION), nullable=True)

    # Relationships
    document = relationship("KnowledgeDocument", back_populates="chunks")
