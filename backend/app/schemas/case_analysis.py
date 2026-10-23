"""
Case Analysis and Hypothesis Schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class HypothesisItem(BaseModel):
    id: str = Field(..., description="Unique ID for hypothesis (e.g. hyp_1)")
    rank: int = Field(..., ge=1, le=3, description="Rank 1 to 3")
    title: str = Field(..., description="Hypothesis summary")
    description: str = Field(..., description="Detailed explanation")
    probability: float = Field(..., ge=0.0, le=1.0, description="Estimated likelihood")
    supporting_evidence: List[str] = Field(default_factory=list)
    contradictory_evidence: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    best_next_diagnostic_test: str = Field(..., description="Next diagnostic test to prove or refute")


class SeverityBreakdown(BaseModel):
    impact_factor: float
    urgency_factor: float
    scope_factor: float
    sla_risk_factor: float
    final_score: float
    severity_label: str  # low, medium, high, critical
    escalation_decision: bool
    escalation_reason: Optional[str] = None


class CaseAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    intent: str
    sentiment: str
    sentiment_score: float
    urgency: str
    severity_score: float
    severity_label: Optional[str] = "low"
    impact_scope: str
    confirmed_facts: List[str] = Field(default_factory=list)
    hypotheses: List[HypothesisItem] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    escalation_required: bool = False
    severity_breakdown: Optional[SeverityBreakdown] = None
    created_at: datetime
