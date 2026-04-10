"""
Unit tests for QdrantAdapter — Qdrant vector store provider.

Tests verify:
- Upsert chunks with embeddings
- Query returns chunks filtered by org_id
- Query returns empty list for missing org_id
- mark_stale marks chunks as stale
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from uuid import uuid4

from qdrant_client.models import PointStruct

from adapters.outbound.qdrant_adapter import QdrantAdapter
from domain.models import Chunk, SourceType
from tests.fixtures.mock_data import MOCK_ORG_ID, MOCK_CHUNKS, MOCK_EMBEDDING


@pytest.fixture
@patch("adapters.outbound.qdrant_adapter.QdrantClient")
def qdrant_adapter(mock_client_class):
    """QdrantAdapter with mocked QdrantClient."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    adapter = QdrantAdapter(
        api_key="test-key",
        url="http://localhost:6333",
        collection_name="test-collection",
        embedding_dim=1536,
    )
    adapter._client = mock_client
    return adapter


@patch("adapters.outbound.qdrant_adapter.QdrantClient")
def test_qdrant_upsert_chunks(mock_client_class):
    """Upsert should store chunks with embeddings."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    adapter = QdrantAdapter(
        api_key="test-key",
        url="http://localhost:6333",
        collection_name="test-collection",
        embedding_dim=1536,
    )
    adapter._client = mock_client

    adapter.upsert(MOCK_CHUNKS)

    # Client should be called with points
    assert mock_client.upsert.called
    call_args = mock_client.upsert.call_args
    assert call_args.kwargs["collection_name"] == "test-collection"
    assert len(call_args.kwargs["points"]) == len(MOCK_CHUNKS)


@patch("adapters.outbound.qdrant_adapter.QdrantClient")
def test_qdrant_query_filters_by_org_id(mock_client_class):
    """Query should return chunks for specified org_id only."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    adapter = QdrantAdapter(
        api_key="test-key",
        url="http://localhost:6333",
        collection_name="test-collection",
        embedding_dim=1536,
    )
    adapter._client = mock_client

    # Mock search results
    mock_point = MagicMock()
    mock_point.id = 123
    mock_point.payload = {
        "org_id": MOCK_ORG_ID,
        "document_id": "d1",
        "content_text": "Leave policy: 20 days",
        "source_url": "https://example.com/1",
        "source_type": "google_drive",
        "authority_score": 0.7,
        "updated_at": "2025-01-01T00:00:00",
        "is_stale": False,
    }
    mock_client.search.return_value = [mock_point]

    result = adapter.query(
        embedding=MOCK_EMBEDDING,
        query_text="leave policy",
        org_id=MOCK_ORG_ID,
        top_k=10,
    )

    # Should return chunks for correct org
    assert len(result) == 1
    assert result[0].org_id == MOCK_ORG_ID

    # Client search should be called with org_id filter
    assert mock_client.search.called
    call_args = mock_client.search.call_args
    assert "query_filter" in call_args.kwargs


@patch("adapters.outbound.qdrant_adapter.QdrantClient")
def test_qdrant_query_empty_for_wrong_org(mock_client_class):
    """Query should return empty list for missing org_id."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    adapter = QdrantAdapter(
        api_key="test-key",
        url="http://localhost:6333",
        collection_name="test-collection",
        embedding_dim=1536,
    )
    adapter._client = mock_client

    # Mock no results for org_id
    mock_client.search.return_value = []

    result = adapter.query(
        embedding=MOCK_EMBEDDING,
        query_text="leave policy",
        org_id="wrong-org-id",
        top_k=10,
    )

    assert len(result) == 0


@patch("adapters.outbound.qdrant_adapter.QdrantClient")
def test_qdrant_mark_stale(mock_client_class):
    """mark_stale should update chunks is_stale=True."""
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client

    adapter = QdrantAdapter(
        api_key="test-key",
        url="http://localhost:6333",
        collection_name="test-collection",
        embedding_dim=1536,
    )
    adapter._client = mock_client

    # Mock scroll to return points
    mock_point = MagicMock()
    mock_point.id = 123
    mock_point.payload = {"is_stale": False}
    mock_client.scroll.return_value = ([mock_point], None)

    adapter.mark_stale("d1")

    # Client scroll should be called with document_id filter
    assert mock_client.scroll.called
    # Client upsert should be called to mark as stale
    assert mock_client.upsert.called
