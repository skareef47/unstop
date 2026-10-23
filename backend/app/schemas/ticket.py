"""
Ticket Schemas
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class TicketCreate(BaseModel):
    summary: str = Field(..., min_length=5, max_length=1000, description="Brief summary of the issue")
    priority: Optional[str] = Field("medium", pattern="^(low|medium|high|critical)$")
    assigned_team: Optional[str] = Field("l1_support", pattern="^(l1_support|l2_devops|l3_engineering|security_response)$")


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    priority: str
    status: str
    assigned_team: str
    summary: str
    created_at: datetime
    updated_at: datetime


class TicketListResponse(BaseModel):
    items: List[TicketResponse]
    total: int
