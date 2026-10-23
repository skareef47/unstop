"""
Gemini Embedding Provider
"""
from typing import List, Optional
from app.services.embeddings.base import BaseEmbeddingProvider
from app.core.config import settings
from app.core.errors import ProviderException


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        if not self.api_key:
            raise ProviderException("gemini", "GEMINI_API_KEY is not configured")

    def embed_text(self, text: str) -> List[float]:
        from google import genai
        client = genai.Client(api_key=self.api_key)
        response = client.models.embed_content(
            model="text-embedding-004",
            contents=text,
        )
        return response.embeddings[0].values[:settings.EMBEDDING_DIMENSION]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]
