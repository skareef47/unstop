"""
Knowledge Base Seeding Script
"""
import os
import sys

# Ensure backend root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.db.session import SessionLocal, Base, engine
from app.services.knowledge_service import KnowledgeService


def seed_sample_docs():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../knowledge/sample_docs"))
        if not os.path.exists(sample_dir):
            print(f"Directory {sample_dir} not found.")
            return

        for fname in os.listdir(sample_dir):
            if fname.endswith(".md") or fname.endswith(".txt"):
                fpath = os.path.join(sample_dir, fname)
                with open(fpath, "rb") as f:
                    content = f.read()

                title = fname.replace("_", " ").replace(".md", "").title()
                doc = KnowledgeService.ingest_document(
                    db=db,
                    title=title,
                    source=fname,
                    raw_bytes=content,
                    filename=fname,
                    version="1.0",
                )
                print(f"Indexed document: {doc.title} (chunks: {len(doc.chunks)})")
    finally:
        db.close()


if __name__ == "__main__":
    seed_sample_docs()
