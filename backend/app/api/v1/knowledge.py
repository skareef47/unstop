"""
Knowledge Base API Endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.knowledge import (
    KnowledgeDocumentResponse,
    KnowledgeSearchResponse,
)
from app.services.knowledge_service import KnowledgeService
from app.core.config import settings
from app.core.errors import BadRequestException, NotFoundException

router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


@router.post("/documents", response_model=KnowledgeDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    version: Optional[str] = Form("1.0"),
    db: Session = Depends(get_db),
):
    """
    Upload and index a Markdown, TXT, or PDF runbook into semantic vector search.
    """
    raw_bytes = await file.read()
    if len(raw_bytes) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise BadRequestException(f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_BYTES} bytes.")

    doc_title = title or file.filename or "Untitled Document"
    doc = KnowledgeService.ingest_document(
        db=db,
        title=doc_title,
        source=file.filename or "upload",
        raw_bytes=raw_bytes,
        filename=file.filename or "doc.txt",
        version=version or "1.0",
    )
    resp = KnowledgeDocumentResponse.model_validate(doc)
    resp.chunk_count = len(doc.chunks)
    return resp


@router.get("/documents", response_model=List[KnowledgeDocumentResponse])
def list_documents(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List indexed knowledge base documents."""
    skip = (page - 1) * limit
    docs = KnowledgeService.list_documents(db=db, skip=skip, limit=limit)
    response_items = []
    for d in docs:
        resp = KnowledgeDocumentResponse.model_validate(d)
        resp.chunk_count = len(d.chunks)
        response_items.append(resp)
    return response_items


@router.get("/documents/{document_id}", response_model=KnowledgeDocumentResponse)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve details of a knowledge document."""
    doc = KnowledgeService.get_document(db=db, doc_id=document_id)
    if not doc:
        raise NotFoundException("KnowledgeDocument", document_id)
    resp = KnowledgeDocumentResponse.model_validate(doc)
    resp.chunk_count = len(doc.chunks)
    return resp


@router.delete("/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
):
    """Delete a document and all its indexed vector chunks."""
    KnowledgeService.delete_document(db=db, doc_id=document_id)
    return None


@router.get("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    q: str = Query(..., min_length=1, description="Search query"),
    top_k: int = Query(4, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """Semantic vector similarity search across indexed knowledge."""
    results = KnowledgeService.search(db=db, query=q, top_k=top_k)
    return KnowledgeSearchResponse(query=q, results=results)
