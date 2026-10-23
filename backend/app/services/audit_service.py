"""
Audit Logging Service
"""
from typing import Any, Dict, Optional
from sqlalchemy.orm import Session
from app.models.audit import AuditEvent
from app.policies.safety_policy import sanitize_audit_payload


class AuditService:
    @staticmethod
    def log_event(
        db: Session,
        actor: str,
        event_type: str,
        payload: Dict[str, Any],
        conversation_id: Optional[str] = None,
    ) -> AuditEvent:
        clean_payload = sanitize_audit_payload(payload)
        event = AuditEvent(
            conversation_id=conversation_id,
            actor=actor,
            event_type=event_type,
            payload=clean_payload,
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event
