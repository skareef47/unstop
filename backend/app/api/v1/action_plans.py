"""
Action Plans API Endpoints
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.action_plan import (
    ActionPlanResponse,
    PlanApprovalRequest,
)
from app.services.action_plan_service import ActionPlanService
from app.core.errors import NotFoundException

router = APIRouter(tags=["Action Plans"])


@router.post("/conversations/{conversation_id}/action-plan", response_model=ActionPlanResponse, status_code=status.HTTP_201_CREATED)
def generate_action_plan(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    """Generate structured action plan based on case history and findings."""
    plan = ActionPlanService.generate_plan(db=db, conversation_id=conversation_id)
    return plan


@router.get("/conversations/{conversation_id}/action-plan", response_model=ActionPlanResponse)
def get_latest_action_plan(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve the latest action plan for a conversation."""
    plan = ActionPlanService.get_latest_plan(db=db, conversation_id=conversation_id)
    if not plan:
        raise NotFoundException("ActionPlan for conversation", conversation_id)
    return plan


@router.post("/action-plans/{plan_id}/approve", response_model=ActionPlanResponse)
def approve_action_plan(
    plan_id: str,
    payload: PlanApprovalRequest = PlanApprovalRequest(),
    db: Session = Depends(get_db),
):
    """Approve a proposed action plan for execution."""
    plan = ActionPlanService.approve_plan(db=db, plan_id=plan_id, actor="agent")
    return plan


@router.post("/action-plans/{plan_id}/reject", response_model=ActionPlanResponse)
def reject_action_plan(
    plan_id: str,
    payload: PlanApprovalRequest = PlanApprovalRequest(),
    db: Session = Depends(get_db),
):
    """Reject a proposed action plan."""
    plan = ActionPlanService.reject_plan(db=db, plan_id=plan_id, actor="agent")
    return plan
