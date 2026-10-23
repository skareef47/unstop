"""
Conversations API Endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.conversation import (
    ConversationCreate,
    ConversationResponse,
    ConversationListResponse,
)
from app.schemas.message import MessageCreate, MessageSubmitResponse
from app.schemas.case_analysis import CaseAnalysisResponse
from app.services.conversation_service import ConversationService
from app.services.classification_service import ClassificationService
from app.core.errors import NotFoundException

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
):
    """Create a new troubleshooting conversation session."""
    conv = ConversationService.create_conversation(
        db=db,
        product_area=payload.product_area,
        environment=payload.environment,
    )
    return conv


@router.get("", response_model=ConversationListResponse)
def list_conversations(
    status: Optional[str] = Query(None, description="Filter by status"),
    product_area: Optional[str] = Query(None, description="Filter by product area"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """List conversations with pagination and status/product_area filtering."""
    skip = (page - 1) * limit
    items, total = ConversationService.list_conversations(
        db=db, status=status, product_area=product_area, skip=skip, limit=limit
    )
    response_items = []
    for item in items:
        resp = ConversationResponse.model_validate(item)
        resp.message_count = len(item.messages)
        response_items.append(resp)

    return ConversationListResponse(items=response_items, total=total, page=page, limit=limit)


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve detailed conversation state."""
    conv = ConversationService.get_conversation(db=db, conversation_id=conversation_id)
    if not conv:
        raise NotFoundException("Conversation", conversation_id)
    resp = ConversationResponse.model_validate(conv)
    resp.message_count = len(conv.messages)
    return resp


@router.post("/{conversation_id}/messages", response_model=MessageSubmitResponse)
def submit_message(
    conversation_id: str,
    payload: MessageCreate,
    db: Session = Depends(get_db),
):
    """Submit a customer or agent message and receive evidence-grounded AI reply."""
    return ConversationService.submit_message(
        db=db,
        conversation_id=conversation_id,
        content=payload.content,
        client_message_id=payload.client_message_id,
    )


@router.post("/{conversation_id}/analyze", response_model=CaseAnalysisResponse)
def recompute_analysis(
    conversation_id: str,
    db: Session = Depends(get_db),
):
    """Recompute structured case analysis, hypotheses, and severity scoring."""
    analysis = ClassificationService.analyze_conversation(db=db, conversation_id=conversation_id)
    return analysis
