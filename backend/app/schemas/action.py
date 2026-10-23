"""
Simulated Action Schemas
"""
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class SimulatedActionRequest(BaseModel):
    action_key: str = Field(..., description="Action to simulate: mock_config_correction, mock_health_check, mock_service_escalation, mock_compensation")
    parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Parameters for action simulation")
    confirmed_approval: bool = Field(False, description="Explicit approval acknowledgement for consequential actions")


class SimulatedActionResponse(BaseModel):
    action_key: str
    status: str  # success, failed, rejected
    execution_id: str
    result: Dict[str, Any]
    audit_event_id: str
    message: str
