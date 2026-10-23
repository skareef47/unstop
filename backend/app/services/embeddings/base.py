"""
Base Embedding Provider Interface
"""
from abc import ABC, abstractmethod
from typing import List
import numpy as np


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for a single text."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embedding vectors for multiple texts."""
        pass

    def similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        v1 = np.array(vec1, dtype=np.float32)
        v2 = np.array(vec2, dtype=np.float32)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))
