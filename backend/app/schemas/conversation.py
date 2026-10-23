"""
Conversation Schemas
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ConversationCreate(BaseModel):
    product_area: str = Field(default="api_gateway", description="Service or product domain")
    environment: str = Field(default="production", description="Environment affected: production, staging, dev")


class ConversationUpdate(BaseModel):
    status: Optional[str] = Field(None, description="New status")
    product_area: Optional[str] = None
    environment: Optional[str] = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    product_area: str
    environment: str
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0


class ConversationListResponse(BaseModel):
    items: List[ConversationResponse]
    total: int
    page: int
    limit: int
