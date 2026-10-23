"""
Deterministic Local Fast Feature Hashing Embeddings
"""
import hashlib
import re
from typing import List
import numpy as np
from app.services.embeddings.base import BaseEmbeddingProvider
from app.core.config import settings


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """
    Fast, deterministic dense embedding provider without heavy ML dependencies.
    Hashes words and subword character n-grams into a fixed 384-dimensional vector
    with L2 normalization.
    """

    def __init__(self, dimension: int = 384):
        self.dimension = dimension or settings.EMBEDDING_DIMENSION

    def _tokenize(self, text: str) -> List[str]:
        cleaned = re.sub(r"[^\w\s-]", " ", text.lower())
        words = [w for w in cleaned.split() if len(w) > 1]
        tokens = list(words)
        # Add character tri-grams for subword matching
        for word in words:
            if len(word) >= 3:
                for i in range(len(word) - 2):
                    tokens.append(word[i : i + 3])
        return tokens

    def embed_text(self, text: str) -> List[float]:
        vector = np.zeros(self.dimension, dtype=np.float32)
        tokens = self._tokenize(text)
        if not tokens:
            # Return unit vector pointing in first dimension for empty text
            vector[0] = 1.0
            return vector.tolist()

        for token in tokens:
            # Deterministic hash to dimension index
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dimension
            sign = 1.0 if (h >> 8) % 2 == 0 else -1.0
            vector[idx] += sign

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        else:
            vector[0] = 1.0

        return vector.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]
