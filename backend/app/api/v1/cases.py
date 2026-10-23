"""
Case Actions API Endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.action import SimulatedActionRequest, SimulatedActionResponse
from app.services.action_service import ActionService

router = APIRouter(tags=["Case Actions"])


@router.post("/cases/{conversation_id}/actions", response_model=SimulatedActionResponse)
def execute_case_action(
    conversation_id: str,
    payload: SimulatedActionRequest,
    x_actor_role: Optional[str] = Header("agent", alias="X-Actor-Role"),
    x_actor_name: Optional[str] = Header("agent_user", alias="X-Actor-Name"),
    db: Session = Depends(get_db),
):
    """
    Execute an authorized simulated diagnostic or remediation action.
    Consequential actions require confirmed_approval=True and proper role.
    """
    response = ActionService.execute_action(
        db=db,
        conversation_id=conversation_id,
        action_key=payload.action_key,
        parameters=payload.parameters,
        confirmed_approval=payload.confirmed_approval,
        actor=x_actor_name or "agent_user",
        actor_role=x_actor_role or "agent",
    )
    return response
