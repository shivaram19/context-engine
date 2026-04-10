"""
E2E smoke tests for HTTP endpoints.

Tests verify:
- GET /chat returns chat UI (200 with HTML)
- POST /api/v1/query returns answer with citations
- Error handling returns proper error response
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from domain.models import QueryResult
from tests.fixtures.mock_data import (
    MOCK_ORG_ID,
    MOCK_LLM_ANSWER,
)


def make_mock_container():
    """Create a mock container with QueryService."""
    mock_qs = MagicMock()
    mock_qs.query.return_value = QueryResult(
        answer=MOCK_LLM_ANSWER,
        citations=[
            {
                "title": "HR Policy 2025",
                "url": "https://drive.google.com/file/d/1",
                "source_type": "google_drive",
                "updated_at": "2025-01-01T00:00:00",
            }
        ],
        response_language="en",
        latency_ms={
            "detect_ms": 1,
            "translate_ms": 0,
            "embed_ms": 20,
            "retrieve_ms": 30,
            "generate_ms": 400,
        },
    )
    return {"query_service": mock_qs, "ingestion_service": MagicMock()}


@patch("infra.container.get_container", return_value=make_mock_container())
def test_chat_ui_returns_200(mock_container):
    """GET /chat should return 200 with HTML content."""
    from infra.main import app

    client = TestClient(app)
    response = client.get("/chat")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


@patch("infra.container.get_container", return_value=make_mock_container())
def test_query_endpoint_returns_answer(mock_container):
    """POST /api/v1/query should return answer with citations."""
    from infra.main import app

    client = TestClient(app)
    response = client.post(
        "/api/v1/query",
        json={
            "query": "what is our leave policy?",
            "org_id": MOCK_ORG_ID,
            "company_name": "Acme Corp",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == MOCK_LLM_ANSWER
    assert len(data["citations"]) >= 1
    assert "detect_ms" in data["latency_ms"]
    assert "embed_ms" in data["latency_ms"]
    assert "retrieve_ms" in data["latency_ms"]
    assert "generate_ms" in data["latency_ms"]


@patch("infra.container.get_container", return_value=make_mock_container())
def test_query_endpoint_error_handling(mock_container):
    """POST /api/v1/query with invalid payload should handle gracefully."""
    from infra.main import app

    client = TestClient(app)

    # Missing required fields
    response = client.post(
        "/api/v1/query",
        json={
            "query": "what is our leave policy?",
            # Missing org_id
        },
    )

    # Should return validation error (422)
    assert response.status_code == 422
