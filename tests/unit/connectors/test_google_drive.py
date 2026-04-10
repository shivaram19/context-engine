"""
Unit tests for Google Drive connector.
All Google Drive API calls are mocked.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, Mock

from adapters.connectors.google_drive import GoogleDriveConnector
from domain.models import SourceType


@pytest.fixture
def mock_credentials():
    """Mock Google Drive credentials."""
    return {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
    }


@pytest.fixture
def connector_with_mock_service(mock_credentials):
    """Create connector with mocked Drive service."""
    with patch("adapters.connectors.google_drive.build") as mock_build:
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        connector = GoogleDriveConnector(
            credentials=mock_credentials,
            org_id="test-org-id",
        )
        connector._service = mock_service
        return connector, mock_service


def test_fetch_returns_documents(connector_with_mock_service):
    """Test that fetch_documents returns Document objects."""
    connector, mock_service = connector_with_mock_service

    # Mock Drive API response
    mock_service.files().list.return_value.execute.return_value = {
        "files": [
            {
                "id": "file1",
                "name": "Test Document",
                "mimeType": "application/vnd.google-apps.document",
                "modifiedTime": "2026-03-23T10:00:00Z",
                "webViewLink": "https://docs.google.com/document/d/file1",
                "size": 1000,
            }
        ]
    }
    mock_service.files().list_next.return_value = None

    # Mock file download
    mock_service.files().export_media.return_value.execute.return_value = b"Document content here"

    # Fetch documents
    docs = connector.fetch_documents(org_id="test-org-id")

    # Assertions
    assert len(docs) == 1
    assert docs[0].id == "file1"
    assert docs[0].org_id == "test-org-id"
    assert docs[0].source_type == SourceType.GOOGLE_DRIVE
    assert docs[0].title == "Test Document"
    assert docs[0].authority_score == 0.7
    assert docs[0].content == "Document content here"


def test_fetch_handles_api_error_gracefully(connector_with_mock_service):
    """Test that API errors don't raise — returns empty list."""
    connector, mock_service = connector_with_mock_service

    # Mock Drive API to raise error
    mock_service.files().list.return_value.execute.side_effect = Exception("API Error")

    # Fetch should not raise
    docs = connector.fetch_documents(org_id="test-org-id")

    # Should return empty list, not raise
    assert docs == []


def test_unsupported_mime_type_skipped(connector_with_mock_service):
    """Test that unsupported MIME types are skipped."""
    connector, mock_service = connector_with_mock_service

    # Mock Drive API response with spreadsheet (unsupported)
    mock_service.files().list.return_value.execute.return_value = {
        "files": [
            {
                "id": "sheet1",
                "name": "Spreadsheet",
                "mimeType": "application/vnd.google-apps.spreadsheet",
                "modifiedTime": "2026-03-23T10:00:00Z",
                "webViewLink": "https://docs.google.com/spreadsheets/d/sheet1",
                "size": 1000,
            }
        ]
    }
    mock_service.files().list_next.return_value = None

    # Fetch should skip the spreadsheet
    docs = connector.fetch_documents(org_id="test-org-id")

    # Should return empty list (spreadsheet unsupported)
    assert docs == []


def test_empty_file_skipped(connector_with_mock_service):
    """Test that empty files are skipped."""
    connector, mock_service = connector_with_mock_service

    # Mock Drive API response with empty file
    mock_service.files().list.return_value.execute.return_value = {
        "files": [
            {
                "id": "empty_file",
                "name": "Empty Document",
                "mimeType": "application/vnd.google-apps.document",
                "modifiedTime": "2026-03-23T10:00:00Z",
                "webViewLink": "https://docs.google.com/document/d/empty_file",
                "size": 0,  # Empty file
            }
        ]
    }
    mock_service.files().list_next.return_value = None

    # Fetch should skip the empty file
    docs = connector.fetch_documents(org_id="test-org-id")

    # Should return empty list
    assert docs == []


def test_source_type():
    """Test that source_type returns GOOGLE_DRIVE."""
    with patch("adapters.connectors.google_drive.build"):
        connector = GoogleDriveConnector(
            credentials={"access_token": "test"},
            org_id="test-org",
        )
        assert connector.source_type() == SourceType.GOOGLE_DRIVE


def test_auth_error_raises_value_error():
    """Test that auth errors raise ValueError with clear message."""
    with patch("adapters.connectors.google_drive.Credentials") as mock_creds:
        mock_creds.side_effect = Exception("Invalid credentials")

        with pytest.raises(ValueError) as exc_info:
            GoogleDriveConnector(
                credentials={"access_token": "invalid"},
                org_id="test-org",
            )

        assert "Failed to authenticate" in str(exc_info.value)


def test_fetch_with_since_filter(connector_with_mock_service):
    """Test that since filter is applied to API query."""
    connector, mock_service = connector_with_mock_service

    # Mock Drive API
    mock_service.files().list.return_value.execute.return_value = {"files": []}
    mock_service.files().list_next.return_value = None

    # Fetch with since filter
    since_time = "2026-03-20T00:00:00Z"
    docs = connector.fetch_documents(org_id="test-org-id", since=since_time)

    # Verify list() was called with since in query
    call_args = mock_service.files().list.call_args
    assert "modifiedTime" in call_args[1]["q"]


def test_all_supported_mime_types(connector_with_mock_service):
    """Test that all documented MIME types are handled."""
    connector, mock_service = connector_with_mock_service

    supported = [
        "application/vnd.google-apps.document",
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
    ]

    for mime_type in supported:
        # Mock Drive API response
        mock_service.files().list.return_value.execute.return_value = {
            "files": [
                {
                    "id": f"file_{mime_type}",
                    "name": f"Test {mime_type}",
                    "mimeType": mime_type,
                    "modifiedTime": "2026-03-23T10:00:00Z",
                    "webViewLink": f"https://example.com/{mime_type}",
                    "size": 1000,
                }
            ]
        }
        mock_service.files().list_next.return_value = None

        # Mock download (use export for Google Docs, get for others)
        if mime_type == "application/vnd.google-apps.document":
            mock_service.files().export_media.return_value.execute.return_value = b"Content"
        else:
            mock_service.files().get_media.return_value.execute.return_value = b"Content"

        # Fetch
        docs = connector.fetch_documents(org_id="test-org-id")

        # Should not skip any supported type
        assert len(docs) == 1
        assert docs[0].source_type == SourceType.GOOGLE_DRIVE
