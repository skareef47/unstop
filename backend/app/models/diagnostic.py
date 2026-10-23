"""
DiagnosticRun and DiagnosticStep Models
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base


class DiagnosticRun(Base):
    __tablename__ = "diagnostic_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_key = Column(String(100), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="running", index=True)  # running, passed, failed, escalated, completed
    current_step = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="diagnostic_runs")
    steps = relationship("DiagnosticStep", back_populates="run", cascade="all, delete-orphan", order_by="DiagnosticStep.executed_at")


class DiagnosticStep(Base):
    __tablename__ = "diagnostic_steps"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    run_id = Column(String(36), ForeignKey("diagnostic_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_key = Column(String(100), nullable=False)
    instruction = Column(Text, nullable=False)
    result = Column(String(50), nullable=False, default="pending")  # passed, failed, inconclusive
    evidence = Column(JSON, nullable=False, default=dict)
    executed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    run = relationship("DiagnosticRun", back_populates="steps")
