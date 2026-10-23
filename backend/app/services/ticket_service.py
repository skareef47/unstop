"""
Ticket Management Service
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.conversation import Conversation
from app.models.ticket import Ticket
from app.services.audit_service import AuditService
from app.websockets.manager import ws_manager
from app.core.errors import NotFoundException


class TicketService:
    @staticmethod
    def create_ticket(
        db: Session,
        conversation_id: str,
        summary: str,
        priority: str = "medium",
        assigned_team: str = "l1_support",
        actor: str = "agent",
    ) -> Ticket:
        conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
        if not conversation:
            raise NotFoundException("Conversation", conversation_id)

        ticket = Ticket(
            conversation_id=conversation_id,
            summary=summary,
            priority=priority,
            assigned_team=assigned_team,
            status="open",
        )
        db.add(ticket)
        db.commit()
        db.refresh(ticket)

        # Audit Event
        AuditService.log_event(
            db=db,
            actor=actor,
            event_type="ticket.created",
            payload={
                "ticket_id": ticket.id,
                "priority": ticket.priority,
                "assigned_team": ticket.assigned_team,
                "summary": ticket.summary,
            },
            conversation_id=conversation_id,
        )

        # Broadcast
        ws_manager.broadcast_sync(
            event_type="ticket.created",
            data={
                "ticket_id": ticket.id,
                "priority": ticket.priority,
                "assigned_team": ticket.assigned_team,
                "status": ticket.status,
                "summary": ticket.summary,
            },
            conversation_id=conversation_id,
        )

        return ticket

    @staticmethod
    def list_tickets(
        db: Session,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Ticket]:
        q = db.query(Ticket)
        if status:
            q = q.filter(Ticket.status == status)
        if priority:
            q = q.filter(Ticket.priority == priority)
        return q.order_by(Ticket.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_ticket(db: Session, ticket_id: str) -> Optional[Ticket]:
        return db.query(Ticket).filter(Ticket.id == ticket_id).first()
