"""
OpenAI embedding provider adapter.
Implements EmbeddingProvider port using text-embedding-3-small model.
"""

import logging
from typing import Optional

import openai

from ports.embedding_provider import EmbeddingProvider

logger = logging.getLogger(__name__)


class OpenAIEmbedAdapter(EmbeddingProvider):
    """
    Implements EmbeddingProvider using OpenAI's text-embedding-3-small.
    Batch size: max 100 texts per API call.
    Dimensions: 1536.
    """

    MODEL = "text-embedding-3-small"
    DIMENSIONS = 1536
    MAX_BATCH_SIZE = 100

    def __init__(self, api_key: str):
        """Initialize OpenAI client."""
        self._client = openai.OpenAI(api_key=api_key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Convert texts to embeddings in batches.
        Max 100 texts per API call (OpenAI limit).
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        try:
            # Process in batches of max 100
            for i in range(0, len(texts), self.MAX_BATCH_SIZE):
                batch = texts[i : i + self.MAX_BATCH_SIZE]

                response = self._client.embeddings.create(
                    model=self.MODEL,
                    input=batch,
                )

                # Extract embeddings in order
                batch_embeddings = sorted(response.data, key=lambda x: x.index)
                all_embeddings.extend([e.embedding for e in batch_embeddings])

            return all_embeddings

        except Exception as e:
            logger.error(f"[OpenAIEmbedAdapter] embed failed: {e}")
            raise

    def dimensions(self) -> int:
        """Return embedding dimensions (1536 for text-embedding-3-small)."""
        return self.DIMENSIONS
