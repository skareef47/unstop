"""
Action Plan Schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class ActionRecommendation(BaseModel):
    action_key: str = Field(..., description="Machine identifier (e.g. rotate_token_cache)")
    title: str = Field(..., description="Human readable action title")
    rationale: str = Field(..., description="Why this action is recommended")
    risk_level: str = Field(default="low", description="low, medium, high")
    required_role: str = Field(default="agent", description="customer, agent, l2_devops, security_admin")
    requires_approval: bool = Field(default=True, description="Consequential actions require human approval")


class ActionPlanGenerateRequest(BaseModel):
    notes: Optional[str] = Field(None, description="Optional extra notes from agent")


class ActionPlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    summary: str
    customer_impact: str
    confirmed_findings: List[str] = Field(default_factory=list)
    steps_attempted: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[ActionRecommendation] = Field(default_factory=list)
    required_evidence: List[str] = Field(default_factory=list)
    recommended_team: str
    escalation_reason: Optional[str] = None
    status: str  # draft, approved, rejected, executed
    created_at: datetime
    approved_at: Optional[datetime] = None


class PlanApprovalRequest(BaseModel):
    reviewer_notes: Optional[str] = Field(None, description="Approval or rejection notes")
