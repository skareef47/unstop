"""
Embeddings Package
"""
from app.services.embeddings.base import BaseEmbeddingProvider
from app.services.embeddings.local_provider import LocalEmbeddingProvider
from app.services.embeddings.openai_provider import OpenAIEmbeddingProvider
from app.services.embeddings.gemini_provider import GeminiEmbeddingProvider
from app.services.embeddings.factory import get_embedding_provider, set_embedding_provider

__all__ = [
    "BaseEmbeddingProvider",
    "LocalEmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "GeminiEmbeddingProvider",
    "get_embedding_provider",
    "set_embedding_provider",
]
