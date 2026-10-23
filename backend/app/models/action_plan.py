"""
ActionPlan Model
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class ActionPlan(Base):
    __tablename__ = "action_plans"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    summary = Column(Text, nullable=False)
    customer_impact = Column(Text, nullable=False)
    confirmed_findings = Column(JSON, nullable=False, default=list)
    steps_attempted = Column(JSON, nullable=False, default=list)
    recommendations = Column(JSON, nullable=False, default=list)
    required_evidence = Column(JSON, nullable=False, default=list)
    recommended_team = Column(String(100), nullable=False, default="l1_support")
    escalation_reason = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="draft", index=True)  # draft, approved, rejected, executed
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="action_plans")
