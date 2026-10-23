"""
AuditEvent Model
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True, index=True)
    actor = Column(String(100), nullable=False, default="system")  # customer, agent, system, ai_assistant
    event_type = Column(String(100), nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="audit_events")
