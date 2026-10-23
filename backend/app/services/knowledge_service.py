"""
Knowledge Retrieval and Ingestion Pipeline
"""
import hashlib
import io
import re
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.knowledge import KnowledgeDocument, KnowledgeChunk
from app.schemas.knowledge import KnowledgeSearchResult
from app.schemas.message import Citation
from app.services.embeddings.factory import get_embedding_provider
from app.core.errors import BadRequestException, NotFoundException


class KnowledgeService:
    @staticmethod
    def extract_text(raw_bytes: bytes, filename: str) -> str:
        """Extract plain text from Markdown, TXT, or PDF files."""
        lower_fn = filename.lower()
        if lower_fn.endswith(".pdf"):
            try:
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(raw_bytes))
                text_parts = []
                for idx, page in enumerate(reader.pages):
                    extracted = page.extract_text()
                    if extracted:
                        text_parts.append(f"## Page {idx + 1}\n{extracted}")
                return "\n\n".join(text_parts)
            except Exception as e:
                raise BadRequestException(f"Failed to extract text from PDF: {e}")
        else:
            try:
                return raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return raw_bytes.decode("latin-1", errors="replace")

    @staticmethod
    def split_into_chunks(text: str, document_title: str) -> List[Dict[str, Any]]:
        """
        Split text into logical sections preserving Markdown headers and context.
        """
        sections = []
        current_section = "Overview"
        current_lines = []

        lines = text.split("\n")
        for line in lines:
            header_match = re.match(r"^(#{1,3})\s+(.+)$", line.strip())
            if header_match:
                if current_lines:
                    section_content = "\n".join(current_lines).strip()
                    if section_content:
                        sections.append({"section": current_section, "content": section_content})
                    current_lines = []
                current_section = header_match.group(2).strip()
            else:
                current_lines.append(line)

        if current_lines:
            section_content = "\n".join(current_lines).strip()
            if section_content:
                sections.append({"section": current_section, "content": section_content})

        chunks = []
        # If no markdown sections, split by double newlines or paragraph length
        if not sections:
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            for p in paragraphs:
                chunks.append({"section": "General", "content": p})
            return chunks

        for sec in sections:
            # Further divide long sections if > 1500 chars
            content = sec["content"]
            if len(content) > 1500:
                paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
                buf = ""
                for p in paragraphs:
                    if len(buf) + len(p) > 1200 and buf:
                        chunks.append({"section": sec["section"], "content": buf.strip()})
                        buf = p + "\n\n"
                    else:
                        buf += p + "\n\n"
                if buf.strip():
                    chunks.append({"section": sec["section"], "content": buf.strip()})
            else:
                chunks.append({"section": sec["section"], "content": content})

        return chunks

    @classmethod
    def ingest_document(
        cls,
        db: Session,
        title: str,
        source: str,
        raw_bytes: bytes,
        filename: str,
        version: str = "1.0",
    ) -> KnowledgeDocument:
        """
        Ingest, chunk, embed, and index a document.
        """
        text = cls.extract_text(raw_bytes, filename)
        if not text.strip():
            raise BadRequestException("Uploaded document contains no readable text")

        content_hash = hashlib.sha256(raw_bytes).hexdigest()

        # Check existing document with same content hash
        existing = db.query(KnowledgeDocument).filter(KnowledgeDocument.content_hash == content_hash).first()
        if existing:
            return existing

        doc = KnowledgeDocument(
            title=title,
            source=source,
            version=version,
            status="active",
            content_hash=content_hash,
        )
        db.add(doc)
        db.flush()  # obtain doc.id

        raw_chunks = cls.split_into_chunks(text, title)
        texts_to_embed = [c["content"] for c in raw_chunks]

        embedding_provider = get_embedding_provider()
        embeddings = embedding_provider.embed_batch(texts_to_embed)

        for raw_chunk, emb in zip(raw_chunks, embeddings):
            chunk = KnowledgeChunk(
                document_id=doc.id,
                content=raw_chunk["content"],
                section=raw_chunk["section"],
                chunk_metadata={"title": title, "source": source, "version": version},
                embedding=emb,
            )
            db.add(chunk)

        db.commit()
        db.refresh(doc)
        return doc

    @staticmethod
    def list_documents(db: Session, skip: int = 0, limit: int = 50) -> List[KnowledgeDocument]:
        return db.query(KnowledgeDocument).order_by(KnowledgeDocument.created_at.desc()).offset(skip).limit(limit).all()

    @staticmethod
    def get_document(db: Session, doc_id: str) -> Optional[KnowledgeDocument]:
        return db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()

    @staticmethod
    def delete_document(db: Session, doc_id: str) -> bool:
        doc = db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()
        if not doc:
            raise NotFoundException("KnowledgeDocument", doc_id)
        db.delete(doc)
        db.commit()
        return True

    @classmethod
    def search(
        cls,
        db: Session,
        query: str,
        top_k: int = 4,
        threshold: float = 0.10,
    ) -> List[KnowledgeSearchResult]:
        """
        Semantic search using embeddings.
        Supports SQLite (cosine similarity over candidates) and PostgreSQL (pgvector).
        """
        if not query.strip():
            return []

        embedding_provider = get_embedding_provider()
        query_vector = embedding_provider.embed_text(query)

        results = []
        is_postgres = db.bind and db.bind.dialect.name == "postgresql"

        if is_postgres:
            try:
                # Use native pgvector cosine distance: 1 - cosine_distance = similarity
                chunks = (
                    db.query(KnowledgeChunk, KnowledgeDocument)
                    .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
                    .filter(KnowledgeDocument.status == "active")
                    .order_by(KnowledgeChunk.embedding.cosine_distance(query_vector))
                    .limit(top_k)
                    .all()
                )
                for chunk, doc in chunks:
                    sim = embedding_provider.similarity(query_vector, chunk.embedding)
                    if sim >= threshold:
                        results.append(
                            KnowledgeSearchResult(
                                chunk_id=chunk.id,
                                document_id=doc.id,
                                document_title=doc.title,
                                source=doc.source,
                                section=chunk.section,
                                content=chunk.content,
                                score=round(sim, 3),
                            )
                        )
                return results
            except Exception:
                # Fall back to in-memory similarity if pgvector function error
                pass

        # SQLite / In-Memory Fallback
        all_chunks = (
            db.query(KnowledgeChunk, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
            .filter(KnowledgeDocument.status == "active")
            .all()
        )

        scored = []
        for chunk, doc in all_chunks:
            if chunk.embedding is not None:
                sim = embedding_provider.similarity(query_vector, chunk.embedding)
                if sim >= threshold:
                    scored.append((sim, chunk, doc))

        # Sort descending by similarity
        scored.sort(key=lambda x: x[0], reverse=True)

        for sim, chunk, doc in scored[:top_k]:
            results.append(
                KnowledgeSearchResult(
                    chunk_id=chunk.id,
                    document_id=doc.id,
                    document_title=doc.title,
                    source=doc.source,
                    section=chunk.section,
                    content=chunk.content,
                    score=round(sim, 3),
                )
            )

        return results

    @staticmethod
    def to_citations(results: List[KnowledgeSearchResult]) -> List[Citation]:
        citations = []
        for r in results:
            # First 180 chars as preview snippet
            snippet = r.content[:180] + ("..." if len(r.content) > 180 else "")
            citations.append(
                Citation(
                    document_title=r.document_title,
                    source=r.source,
                    section=r.section,
                    snippet=snippet,
                )
            )
        return citations
