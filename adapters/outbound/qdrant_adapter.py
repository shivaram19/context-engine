"""
Qdrant vector store adapter.
Implements VectorStore port using Qdrant Cloud/local instance.
Supports hybrid search (vector + BM25 sparse vectors) and org_id filtering via payload.
"""

import logging
from datetime import datetime
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from domain.models import Chunk, SourceType
from infra.config import settings
from ports.vector_store import VectorStore

logger = logging.getLogger(__name__)


class QdrantAdapter(VectorStore):
    """
    Implements VectorStore using Qdrant.
    Stores chunks with embeddings and metadata (org_id, document_id, etc.).
    Supports vector search with org_id isolation + optional BM25 hybrid search.
    """

    def __init__(self, api_key: str, url: str, collection_name: str, embedding_dim: int = 1536):
        """Initialize Qdrant client."""
        self._api_key = api_key
        self._url = url
        self._collection_name = collection_name
        self._embedding_dim = embedding_dim
        self._client = None
        self._initialized = False

    def _get_client(self) -> QdrantClient:
        """Lazy initialization of Qdrant client. Only connects when first needed."""
        if self._client is None:
            try:
                self._client = QdrantClient(
                    url=self._url,
                    api_key=self._api_key,
                    prefer_grpc=False,  # REST API for simplicity at MVP
                )
                self._ensure_collection_exists()
                self._ensure_org_id_index()  # Ensure index exists for filtering
                self._initialized = True
            except Exception as e:
                logger.error(f"[QdrantAdapter] Failed to initialize Qdrant client: {e}")
                raise
        return self._client

    def _ensure_org_id_index(self) -> None:
        """Ensure org_id payload index exists for efficient filtering."""
        if self._client is None:
            return
        try:
            logger.debug(f"[QdrantAdapter] Ensuring org_id payload index exists")
            self._client.create_payload_index(
                collection_name=self._collection_name,
                field_name="org_id",
                field_schema="keyword",
            )
            logger.debug(f"[QdrantAdapter] org_id payload index is ready")
        except Exception as e:
            # Index might already exist, which is fine
            logger.debug(f"[QdrantAdapter] org_id payload index result: {e}")

    def _ensure_collection_exists(self) -> None:
        """Create collection if it doesn't exist with org_id index for filtering."""
        if self._client is None:
            return
        try:
            self._client.get_collection(self._collection_name)
            logger.debug(f"[QdrantAdapter] Collection '{self._collection_name}' already exists")
        except Exception:
            # Collection doesn't exist, create it with org_id index
            logger.info(f"[QdrantAdapter] Creating collection: {self._collection_name}")
            self._client.create_collection(
                collection_name=self._collection_name,
                vectors_config=VectorParams(
                    size=self._embedding_dim,
                    distance=Distance.COSINE,
                ),
            )

            # Create an index on org_id for efficient filtering
            logger.info(f"[QdrantAdapter] Creating payload index on 'org_id' field")
            try:
                self._client.create_payload_index(
                    collection_name=self._collection_name,
                    field_name="org_id",
                    field_schema="keyword",
                )
                logger.info(f"[QdrantAdapter] ✅ Payload index on 'org_id' created successfully")
            except Exception as e:
                logger.warning(f"[QdrantAdapter] Could not create org_id index (might already exist): {e}")

    def upsert(self, chunks: list[Chunk]) -> None:
        """
        Store or update chunks with embeddings and metadata.
        Payload includes: org_id, document_id, source_url, source_type, authority_score, etc.
        """
        if not chunks:
            return

        points = []
        for chunk in chunks:
            # Create a unique point ID
            point_id = int(uuid4().int % (2**63 - 1))  # Convert UUID to 64-bit int

            # Payload for filtering and retrieval
            payload = {
                "org_id": str(chunk.org_id),
                "document_id": str(chunk.document_id),
                "content_text": chunk.content_text,
                "source_url": chunk.source_url,
                "source_type": chunk.source_type.value,
                "authority_score": chunk.authority_score,
                "updated_at": chunk.updated_at.isoformat(),
                "is_stale": chunk.is_stale,
            }

            # Create point with embedding
            point = PointStruct(
                id=point_id,
                vector=chunk.embedding or [0.0] * self._embedding_dim,
                payload=payload,
            )
            points.append(point)

        try:
            self._get_client().upsert(
                collection_name=self._collection_name,
                points=points,
            )
            logger.debug(f"[QdrantAdapter] upserted {len(points)} chunks")
        except Exception as e:
            logger.error(f"[QdrantAdapter] upsert failed: {e}")
            raise

    def query(
        self,
        embedding: list[float],
        query_text: str,
        org_id: str,
        top_k: int = 10,
    ) -> list[Chunk]:
        """
        Retrieve top-k chunks for a query embedding.
        Filtered by org_id in payload (tenant isolation).
        Vector search only at MVP (no BM25 fusion yet).
        """
        if not embedding:
            return []

        try:
            # Vector search with org_id filter
            logger.info(f"[QdrantAdapter] Querying with org_id={org_id}, top_k={top_k}")
            query_response = self._get_client().query_points(
                collection_name=self._collection_name,
                query=embedding,
                query_filter={
                    "must": [
                        {
                            "key": "org_id",
                            "match": {"value": str(org_id)},
                        }
                    ]
                },
                limit=top_k,
            )

            chunks = []
            logger.debug(f"[QdrantAdapter] query_response type: {type(query_response)}, has points: {hasattr(query_response, 'points')}")

            # query_points returns a QueryResponse object, access .points
            points = query_response.points if hasattr(query_response, 'points') else query_response
            logger.info(f"[QdrantAdapter] ✅ Retrieved {len(points)} chunks for org_id={org_id}")

            for result in points:
                payload = result.payload
                # Parse updated_at from ISO string back to datetime
                updated_at_str = payload.get("updated_at", "")
                try:
                    updated_at = datetime.fromisoformat(updated_at_str) if updated_at_str else datetime.now()
                except (ValueError, TypeError):
                    updated_at = datetime.now()

                chunk = Chunk(
                    id=str(result.id),
                    org_id=payload.get("org_id", ""),
                    document_id=payload.get("document_id", ""),
                    content_text=payload.get("content_text", ""),
                    source_url=payload.get("source_url", ""),
                    source_type=SourceType(payload.get("source_type", "google_drive")),
                    authority_score=float(payload.get("authority_score", 0.7)),
                    updated_at=updated_at,
                    is_stale=payload.get("is_stale", False),
                    embedding=None,  # Don't return embedding to save bandwidth
                )
                chunks.append(chunk)

            logger.debug(f"[QdrantAdapter] query returned {len(chunks)} chunks for org_id={org_id}")
            return chunks

        except Exception as e:
            logger.error(f"[QdrantAdapter] query failed: {e}")
            raise

    def mark_stale(self, document_id: str) -> None:
        """Mark all chunks from a document as stale (is_stale=True)."""
        try:
            # Get all points with this document_id
            points = self._get_client().scroll(
                collection_name=self._collection_name,
                scroll_filter={
                    "must": [
                        {
                            "key": "document_id",
                            "match": {"value": str(document_id)},
                        }
                    ]
                },
                limit=1000,
            )[0]

            # Update payload to mark as stale
            point_ids = [p.id for p in points]
            if point_ids:
                for point in points:
                    point.payload["is_stale"] = True

                self._get_client().upsert(
                    collection_name=self._collection_name,
                    points=points,
                )
                logger.debug(f"[QdrantAdapter] marked {len(point_ids)} chunks stale for doc {document_id}")

        except Exception as e:
            logger.error(f"[QdrantAdapter] mark_stale failed: {e}")
            raise
