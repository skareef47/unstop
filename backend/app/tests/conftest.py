import os
import sys

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.services.knowledge_service import KnowledgeService
from app.services.llm_provider.mock_provider import MockLLMProvider
from app.services.llm_provider.factory import set_llm_provider
from app.services.embeddings.local_provider import LocalEmbeddingProvider
from app.services.embeddings.factory import set_embedding_provider

# Use in-memory SQLite database with StaticPool for fast, isolated tests
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_providers():
    set_llm_provider(MockLLMProvider())
    set_embedding_provider(LocalEmbeddingProvider())


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database for each test function."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()

    # Pre-seed essential knowledge documents into test db
    sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../knowledge/sample_docs"))
    if os.path.exists(sample_dir):
        for fname in os.listdir(sample_dir):
            if fname.endswith(".md"):
                with open(os.path.join(sample_dir, fname), "rb") as f:
                    content = f.read()
                title = fname.replace("_", " ").replace(".md", "").title()
                KnowledgeService.ingest_document(
                    db=session,
                    title=title,
                    source=fname,
                    raw_bytes=content,
                    filename=fname,
                )

    yield session

    session.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
