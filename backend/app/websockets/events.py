"""
WebSocket Events Definition
"""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from app.policies.safety_policy import redact_sensitive_data, sanitize_audit_payload


class WSEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:12]}")
    event_type: str
    sequence: int
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    conversation_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        event_type: str,
        sequence: int,
        data: Dict[str, Any],
        conversation_id: Optional[str] = None,
    ) -> "WSEvent":
        # Ensure sensitive tokens are redacted from dashboard broadcasts
        clean_data = sanitize_audit_payload(data)
        return cls(
            event_type=event_type,
            sequence=sequence,
            conversation_id=conversation_id,
            data=clean_data,
        )
