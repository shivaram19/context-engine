"""
Ingestion service — fetch documents, chunk, embed, and store.

Single responsibility: take a ConnectorPort, pull documents, chunk, embed, store.
Never let one document failure stop the batch — log and continue.

Zero imports from adapters/ or infra/
"""

import logging

from domain.models import Chunk
from ports.connector_port import ConnectorPort
from ports.document_parser import DocumentParser
from ports.embedding_provider import EmbeddingProvider
from ports.vector_store import VectorStore
from services.chunking_service import ChunkingService

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Ingest documents from a source, chunk them, embed them, and store them.

    Pipeline:
      1. Fetch documents from connector
      2. Parse raw content
      3. Chunk documents using ChunkingService
      4. Embed chunks using EmbeddingProvider
      5. Store in VectorStore

    Dependencies injected via constructor (Dependency Inversion Principle).
    All dependencies are ports (abstractions), never concrete adapters.
    """

    def __init__(
        self,
        parser: DocumentParser,
        chunker: ChunkingService,
        embedder: EmbeddingProvider,
        store: VectorStore,
    ):
        """Initialize with port dependencies."""
        self._parser = parser
        self._chunker = chunker
        self._embedder = embedder
        self._store = store

    def ingest(self, connector: ConnectorPort, org_id: str, since=None) -> int:
        """
        Ingest documents from a connector.

        Args:
            connector: ConnectorPort implementation (Google Drive, GitHub, etc.)
            org_id: Organization ID for tenant isolation
            since: Optional timestamp to fetch documents modified after this time

        Returns:
            Number of chunks indexed
        """
        logger.info(f"[IngestionService] Starting ingest from {connector.source_type().value} for org_id={org_id}")

        try:
            documents = connector.fetch_documents(org_id=org_id, since=since)
            logger.info(f"[IngestionService] Fetched {len(documents)} documents from connector")

            if not documents:
                logger.warning("[IngestionService] No documents fetched from connector")
                return 0

            total_chunks = 0

            for idx, doc in enumerate(documents, 1):
                try:
                    logger.debug(f"[IngestionService] Processing document {idx}/{len(documents)}: {doc.source_url}")

                    # Chunk the document
                    chunks = self._chunker.chunk(doc)
                    logger.debug(f"[IngestionService] Document created {len(chunks)} chunks")

                    if not chunks:
                        logger.debug(f"[IngestionService] No chunks from {doc.source_url}")
                        continue

                    # Embed all chunks
                    texts = [c.content_text for c in chunks]
                    logger.debug(f"[IngestionService] Embedding {len(texts)} chunks...")

                    try:
                        embeddings = self._embedder.embed(texts)
                        logger.debug(f"[IngestionService] Received {len(embeddings)} embeddings")
                    except Exception as e:
                        logger.error(f"[IngestionService] Embedding failed for {doc.source_url}: {e}", exc_info=True)
                        continue

                    # Assign embeddings to chunks
                    for chunk, embedding in zip(chunks, embeddings):
                        chunk.embedding = embedding

                    # Store chunks in vector DB
                    try:
                        self._store.upsert(chunks)
                        total_chunks += len(chunks)
                        logger.info(f"[IngestionService] ✅ indexed {len(chunks)} chunks from {doc.source_url}")
                    except Exception as e:
                        logger.error(f"[IngestionService] Vector store upsert failed for {doc.source_url}: {e}", exc_info=True)
                        continue

                except Exception as e:
                    # Never let one document failure stop the entire batch
                    logger.error(f"[IngestionService] ❌ failed to ingest {doc.source_url}: {e}", exc_info=True)
                    continue

            logger.info(f"[IngestionService] ✅ ingest completed: {total_chunks} total chunks indexed")
            return total_chunks

        except Exception as e:
            logger.error(f"[IngestionService] Fatal error during ingest: {e}", exc_info=True)
            return 0
