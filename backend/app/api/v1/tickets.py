"""
Tickets API Endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.ticket import TicketCreate, TicketResponse, TicketListResponse
from app.services.ticket_service import TicketService
from app.core.errors import NotFoundException

router = APIRouter(tags=["Tickets"])


@router.post("/conversations/{conversation_id}/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    conversation_id: str,
    payload: TicketCreate,
    db: Session = Depends(get_db),
):
    """Create a new support ticket associated with a conversation."""
    ticket = TicketService.create_ticket(
        db=db,
        conversation_id=conversation_id,
        summary=payload.summary,
        priority=payload.priority or "medium",
        assigned_team=payload.assigned_team or "l1_support",
    )
    return ticket


@router.get("/tickets", response_model=TicketListResponse)
def list_tickets(
    status: Optional[str] = Query(None, description="Filter by status: open, in_progress, resolved, closed"),
    priority: Optional[str] = Query(None, description="Filter by priority: low, medium, high, critical"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List support tickets with pagination and filtering."""
    skip = (page - 1) * limit
    items = TicketService.list_tickets(db=db, status=status, priority=priority, skip=skip, limit=limit)
    total = len(items)
    return TicketListResponse(items=[TicketResponse.model_validate(t) for t in items], total=total)


@router.get("/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve details of a support ticket."""
    ticket = TicketService.get_ticket(db=db, ticket_id=ticket_id)
    if not ticket:
        raise NotFoundException("Ticket", ticket_id)
    return ticket
