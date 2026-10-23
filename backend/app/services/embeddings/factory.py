"""
Embeddings Provider Factory
"""
from typing import Optional
from app.core.config import settings
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings.local_provider import LocalEmbeddingProvider
from app.services.embeddings.openai_provider import OpenAIEmbeddingProvider
from app.services.embeddings.gemini_provider import GeminiEmbeddingProvider

_embedding_instance: Optional[BaseEmbeddingProvider] = None


def get_embedding_provider() -> BaseEmbeddingProvider:
    """Dependency injection for embedding provider."""
    global _embedding_instance
    if _embedding_instance is not None:
        return _embedding_instance

    provider_type = settings.EMBEDDING_PROVIDER.lower()
    if provider_type == "openai":
        try:
            return OpenAIEmbeddingProvider()
        except Exception:
            return LocalEmbeddingProvider()
    elif provider_type == "gemini":
        try:
            return GeminiEmbeddingProvider()
        except Exception:
            return LocalEmbeddingProvider()
    else:
        return LocalEmbeddingProvider()


def set_embedding_provider(provider: BaseEmbeddingProvider) -> None:
    """Override embedding provider for testing."""
    global _embedding_instance
    _embedding_instance = provider
