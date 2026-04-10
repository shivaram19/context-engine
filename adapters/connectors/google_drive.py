"""
Google Drive connector — fetch documents from Google Drive.

Implements ConnectorPort — no service imports this class directly.
Converts Google Drive files to Documents with proper authority scores.
"""

import logging
from datetime import datetime
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from domain.models import Document, SourceType
from ports.connector_port import ConnectorPort

logger = logging.getLogger(__name__)


class GoogleDriveConnector(ConnectorPort):
    """
    Fetches documents from Google Drive.
    Supports: Google Docs, PDF, DOCX, plain text, Markdown.
    Skips: images, videos, folders, spreadsheets.
    Authority score: 0.7 (official docs).
    """

    # MIME types we support
    SUPPORTED_MIME_TYPES = {
        "application/vnd.google-apps.document": "text/plain",  # Google Docs → text
        "application/pdf": "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "application/docx",
        "text/plain": "text/plain",
        "text/markdown": "text/markdown",
    }

    # Export MIME types for Google Docs
    EXPORT_MIME_TYPES = {
        "application/vnd.google-apps.document": "text/plain",
    }

    def __init__(self, credentials: dict, org_id: str):
        """
        Initialize Google Drive connector.

        Args:
            credentials: dict with {access_token, refresh_token, client_id, client_secret}
            org_id: Organization ID for document tagging
        """
        self._org_id = org_id
        self._service = self._build_client(credentials)

    def _build_client(self, credentials: dict):
        """Build authenticated Google Drive service client."""
        try:
            # Build credentials object from dict
            creds = Credentials(
                token=credentials.get("access_token"),
                refresh_token=credentials.get("refresh_token"),
                token_uri="https://oauth2.googleapis.com/token",
                client_id=credentials.get("client_id"),
                client_secret=credentials.get("client_secret"),
            )

            # Refresh if needed
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())

            # Build service
            service = build("drive", "v3", credentials=creds)
            logger.info(f"[GoogleDriveConnector] authenticated for org_id={self._org_id}")
            return service

        except Exception as e:
            logger.error(f"[GoogleDriveConnector] auth failed: {e}")
            raise ValueError(f"Failed to authenticate with Google Drive: {e}")

    def fetch_documents(self, org_id: str, since: Optional[str] = None) -> list[Document]:
        """
        Fetch documents modified after `since`.

        Args:
            org_id: Organization ID (for multi-tenant isolation)
            since: ISO8601 timestamp to filter by modified time

        Returns:
            List of Documents (empty list if error occurs)
        """
        documents = []

        try:
            raw_files = self._fetch_raw(since)
            for file_obj in raw_files:
                doc = self._to_document(file_obj)
                if doc:
                    documents.append(doc)

        except Exception as e:
            logger.error(f"[GoogleDriveConnector] fetch_documents failed: {e}")
            # Do not re-raise — return what we have

        logger.info(f"[GoogleDriveConnector] fetched {len(documents)} documents for org_id={org_id}")
        return documents

    def source_type(self) -> SourceType:
        """Return the source type."""
        return SourceType.GOOGLE_DRIVE

    def _fetch_raw(self, since: Optional[str]) -> list:
        """
        Fetch raw files from Google Drive API.

        Filters by:
        - Supported MIME types
        - Modified time > since (if provided)
        - Not in trash
        """
        try:
            query = "trashed=false"

            # Add supported MIME types filter
            mime_filters = " or ".join(
                [f'mimeType="{mime}"' for mime in self.SUPPORTED_MIME_TYPES.keys()]
            )
            query += f" and ({mime_filters})"

            # Add modified time filter
            if since:
                query += f' and modifiedTime > "{since}"'

            # List files
            request = self._service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name, mimeType, modifiedTime, webViewLink, size)",
                pageSize=100,
            )

            files = []
            while request:
                results = request.execute()
                files.extend(results.get("files", []))
                request = self._service.files().list_next(request, results)

            logger.debug(f"[GoogleDriveConnector] found {len(files)} raw files")
            return files

        except HttpError as e:
            logger.error(f"[GoogleDriveConnector] Drive API error: {e}")
            raise

    def _to_document(self, file_obj: dict) -> Optional[Document]:
        """
        Convert Google Drive file to Document.

        Returns None if:
        - Unsupported MIME type
        - File is empty
        - Download fails

        Never raises.
        """
        try:
            mime_type = file_obj.get("mimeType", "")

            # Check if MIME type is supported
            if mime_type not in self.SUPPORTED_MIME_TYPES:
                logger.debug(
                    f"[GoogleDriveConnector] skip {file_obj.get('name')}: unsupported MIME type {mime_type}"
                )
                return None

            # Skip empty files
            if file_obj.get("size") == 0 or file_obj.get("size") is None:
                logger.debug(
                    f"[GoogleDriveConnector] skip {file_obj.get('name')}: empty file"
                )
                return None

            # Download file content
            content = self._download_file(file_obj)
            if not content:
                logger.debug(f"[GoogleDriveConnector] skip {file_obj.get('name')}: failed to download")
                return None

            # Create Document
            return Document(
                id=file_obj.get("id"),
                org_id=self._org_id,
                source_type=SourceType.GOOGLE_DRIVE,
                source_url=file_obj.get("webViewLink", ""),
                title=file_obj.get("name", ""),
                content=content,
                authority_score=0.7,  # Official docs authority
                updated_at=datetime.fromisoformat(
                    file_obj.get("modifiedTime", "").replace("Z", "+00:00")
                ),
            )

        except Exception as e:
            logger.error(
                f"[GoogleDriveConnector] failed to convert file {file_obj.get('id')}: {e}"
            )
            return None

    def _download_file(self, file_obj: dict) -> Optional[str]:
        """Download file content from Google Drive."""
        try:
            file_id = file_obj.get("id")
            mime_type = file_obj.get("mimeType", "")

            # For Google Docs, export as text
            if mime_type in self.EXPORT_MIME_TYPES:
                request = self._service.files().export_media(
                    fileId=file_id,
                    mimeType=self.EXPORT_MIME_TYPES[mime_type],
                )
            else:
                # For other files, download directly
                request = self._service.files().get_media(fileId=file_id)

            content_bytes = request.execute()
            return content_bytes.decode("utf-8", errors="ignore")

        except Exception as e:
            logger.error(f"[GoogleDriveConnector] download failed for {file_obj.get('id')}: {e}")
            return None
