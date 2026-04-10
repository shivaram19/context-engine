"""
Unit tests for GeminiLLMAdapter — Google Gemini LLM provider.

Tests verify:
- Happy path: generates answer with context
- Rate limit error caught and handled gracefully
- Generic error handled gracefully
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from google.api_core import exceptions

from adapters.outbound.gemini_llm import GeminiLLMAdapter
from domain.models import Chunk, SourceType
from tests.fixtures.mock_data import MOCK_ORG_ID, MOCK_LLM_ANSWER


@pytest.fixture
def mock_chunks():
    """Sample chunks for testing."""
    return [
        Chunk(
            id="c1",
            document_id="d1",
            org_id=MOCK_ORG_ID,
            content_text="Leave policy: 20 days per year",
            source_url="https://drive.google.com/file/d/1",
            source_type=SourceType.GOOGLE_DRIVE,
            authority_score=0.7,
            updated_at=datetime(2025, 1, 1),
            embedding=None,
        )
    ]


@patch("adapters.outbound.gemini_llm.genai")
def test_gemini_happy_path(mock_genai, mock_chunks):
    """Gemini should generate answer from context."""
    # Mock the GenerativeModel
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = MOCK_LLM_ANSWER
    mock_model.generate_content.return_value = mock_response
    mock_genai.GenerativeModel.return_value = mock_model

    adapter = GeminiLLMAdapter(api_key="test-key")
    answer = adapter.generate(
        query="what is our leave policy?",
        context_chunks=mock_chunks,
        response_language="en",
        company_name="Acme Corp",
    )

    assert answer == MOCK_LLM_ANSWER
    assert mock_model.generate_content.called


@patch("adapters.outbound.gemini_llm.genai")
def test_gemini_rate_limit_error_handled(mock_genai, mock_chunks):
    """Gemini rate limit error should be caught and return friendly message."""
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = exceptions.ResourceExhausted("Rate limited")
    mock_genai.GenerativeModel.return_value = mock_model

    adapter = GeminiLLMAdapter(api_key="test-key")
    answer = adapter.generate(
        query="what is our leave policy?",
        context_chunks=mock_chunks,
        response_language="en",
        company_name="Acme Corp",
    )

    # Should return rate limit message, not raise
    assert "currently processing too many requests" in answer


@patch("adapters.outbound.gemini_llm.genai")
def test_gemini_generic_error_handled(mock_genai, mock_chunks):
    """Gemini generic error should be caught and return friendly message."""
    mock_model = MagicMock()
    mock_model.generate_content.side_effect = Exception("API error")
    mock_genai.GenerativeModel.return_value = mock_model

    adapter = GeminiLLMAdapter(api_key="test-key")
    answer = adapter.generate(
        query="what is our leave policy?",
        context_chunks=mock_chunks,
        response_language="en",
        company_name="Acme Corp",
    )

    # Should return error message, not raise
    assert "encountered an error" in answer
