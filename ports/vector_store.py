"""
Vector store port — abstract interface for embedding storage and retrieval.
"""

from abc import ABC, abstractmethod

from domain.models import Chunk


class VectorStore(ABC):
    """Abstraction for vector database operations (Qdrant, Weaviate, etc.)."""

    @abstractmethod
    def upsert(self, chunks: list[Chunk]) -> None:
        """Store or update chunks with their embeddings."""
        ...

    @abstractmethod
    def query(
        self,
        embedding: list[float],
        query_text: str,
        org_id: str,
        top_k: int = 10,
    ) -> list[Chunk]:
        """Retrieve top-k chunks for a query embedding, scoped to org_id."""
        ...

    @abstractmethod
    def mark_stale(self, document_id: str) -> None:
        """Mark all chunks from a document as stale."""
        ...
