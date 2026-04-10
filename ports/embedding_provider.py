"""
Embedding provider port — abstract interface for text embedding models.
"""

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Abstraction for embedding providers (OpenAI, Anthropic, local, etc.)."""

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Convert a list of texts to embeddings."""
        ...

    @abstractmethod
    def dimensions(self) -> int:
        """Return the embedding dimension (e.g., 1536 for text-embedding-3-small)."""
        ...
