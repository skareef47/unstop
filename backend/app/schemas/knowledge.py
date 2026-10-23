"""
Knowledge Schemas
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class KnowledgeDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    source: str
    version: str
    status: str
    content_hash: str
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class KnowledgeSearchResult(BaseModel):
    chunk_id: str
    document_id: str
    document_title: str
    source: str
    section: str
    content: str
    score: float


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: List[KnowledgeSearchResult]
