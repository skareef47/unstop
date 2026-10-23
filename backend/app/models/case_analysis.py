"""
CaseAnalysis Model
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class CaseAnalysis(Base):
    __tablename__ = "case_analyses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    intent = Column(String(100), nullable=False, default="troubleshooting")
    sentiment = Column(String(50), nullable=False, default="neutral")
    sentiment_score = Column(Float, nullable=False, default=0.0)
    urgency = Column(String(50), nullable=False, default="low")
    severity_score = Column(Float, nullable=False, default=0.0)
    impact_scope = Column(String(50), nullable=False, default="single_user")
    confirmed_facts = Column(JSON, nullable=False, default=list)
    hypotheses = Column(JSON, nullable=False, default=list)
    missing_information = Column(JSON, nullable=False, default=list)
    escalation_required = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    conversation = relationship("Conversation", back_populates="case_analyses")
