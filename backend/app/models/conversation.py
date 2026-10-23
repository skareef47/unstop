"""
Conversation Model
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from app.db.session import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    status = Column(String(50), nullable=False, default="active", index=True)  # active, diagnosing, escalated, resolved, closed
    product_area = Column(String(100), nullable=False, default="general", index=True)
    environment = Column(String(50), nullable=False, default="production")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    case_analyses = relationship("CaseAnalysis", back_populates="conversation", cascade="all, delete-orphan", order_by="CaseAnalysis.created_at.desc()")
    diagnostic_runs = relationship("DiagnosticRun", back_populates="conversation", cascade="all, delete-orphan", order_by="DiagnosticRun.created_at.desc()")
    action_plans = relationship("ActionPlan", back_populates="conversation", cascade="all, delete-orphan", order_by="ActionPlan.created_at.desc()")
    tickets = relationship("Ticket", back_populates="conversation", cascade="all, delete-orphan", order_by="Ticket.created_at.desc()")
    audit_events = relationship("AuditEvent", back_populates="conversation", cascade="all, delete-orphan", order_by="AuditEvent.created_at.desc()")
