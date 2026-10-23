"""
Ticket Model
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    priority = Column(String(50), nullable=False, default="medium", index=True)  # low, medium, high, critical
    status = Column(String(50), nullable=False, default="open", index=True)  # open, in_progress, resolved, closed
    assigned_team = Column(String(100), nullable=False, default="l1_support")  # l1_support, l2_devops, l3_engineering, security_response
    summary = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    conversation = relationship("Conversation", back_populates="tickets")
