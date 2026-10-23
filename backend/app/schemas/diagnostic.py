"""
Diagnostic Workflow Schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DiagnosticStartRequest(BaseModel):
    workflow_key: Optional[str] = Field(None, description="Optional explicit workflow key; otherwise deduced from context")


class DiagnosticStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    step_key: str
    instruction: str
    result: str  # pending, passed, failed, inconclusive
    evidence: Dict[str, Any] = Field(default_factory=dict)
    executed_at: datetime


class DiagnosticRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    workflow_key: str
    status: str  # running, passed, failed, escalated, completed
    current_step: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    steps: List[DiagnosticStepResponse] = Field(default_factory=list)


class DiagnosticStepResultRequest(BaseModel):
    result: str = Field(..., pattern="^(passed|failed|inconclusive)$", description="Step outcome: passed, failed, inconclusive")
    evidence: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Diagnostic evidence or output data")
