"""
Diagnostics API Endpoints
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.diagnostic import (
    DiagnosticStartRequest,
    DiagnosticRunResponse,
    DiagnosticStepResultRequest,
)
from app.services.diagnostic_service import DiagnosticService
from app.core.errors import NotFoundException

router = APIRouter(tags=["Diagnostics"])


@router.post("/conversations/{conversation_id}/diagnostics", response_model=DiagnosticRunResponse, status_code=status.HTTP_201_CREATED)
def start_diagnostic_workflow(
    conversation_id: str,
    payload: DiagnosticStartRequest,
    db: Session = Depends(get_db),
):
    """Start an interactive diagnostic troubleshooting workflow for a case."""
    run = DiagnosticService.start_diagnostic_run(
        db=db,
        conversation_id=conversation_id,
        workflow_key=payload.workflow_key,
    )
    return run


@router.get("/diagnostics/{run_id}", response_model=DiagnosticRunResponse)
def get_diagnostic_run(
    run_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve full execution state and step history of a diagnostic run."""
    run = DiagnosticService.get_run(db=db, run_id=run_id)
    if not run:
        raise NotFoundException("DiagnosticRun", run_id)
    return run


@router.post("/diagnostics/{run_id}/steps/{step_id}/result", response_model=DiagnosticRunResponse)
def record_step_result(
    run_id: str,
    step_id: str,
    payload: DiagnosticStepResultRequest,
    db: Session = Depends(get_db),
):
    """Record outcome (passed, failed, inconclusive) for a step and advance state machine."""
    run = DiagnosticService.record_step_result(
        db=db,
        run_id=run_id,
        step_id=step_id,
        result=payload.result,
        evidence=payload.evidence,
    )
    return run
