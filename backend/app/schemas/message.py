"""
Message Schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000, description="Message text from user")
    client_message_id: Optional[str] = Field(None, max_length=100, description="Client-provided idempotency key")


class Citation(BaseModel):
    document_title: str
    source: str
    section: str
    snippet: str


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    client_message_id: Optional[str] = None
    created_at: datetime


class MessageSubmitResponse(BaseModel):
    user_message: MessageResponse
    assistant_message: MessageResponse
    citations: List[Citation] = Field(default_factory=list)
    analysis: Optional[Dict[str, Any]] = None
    diagnostic_suggested: Optional[str] = None
