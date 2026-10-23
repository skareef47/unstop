"""
OpenAI Embedding Provider
"""
from typing import List, Optional
from app.services.embeddings.base import BaseEmbeddingProvider
from app.core.config import settings
from app.core.errors import ProviderException


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            raise ProviderException("openai", "OPENAI_API_KEY is not configured")

    def embed_text(self, text: str) -> List[float]:
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)
        resp = client.embeddings.create(
            input=[text],
            model="text-embedding-3-small",
            dimensions=settings.EMBEDDING_DIMENSION,
        )
        return resp.data[0].embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)
        resp = client.embeddings.create(
            input=texts,
            model="text-embedding-3-small",
            dimensions=settings.EMBEDDING_DIMENSION,
        )
        return [item.embedding for item in resp.data]
