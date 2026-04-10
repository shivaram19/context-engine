"""
Connector port — abstract interface for knowledge source connectors.
"""

from abc import ABC, abstractmethod
from typing import Optional

from domain.models import Document, SourceType


class ConnectorPort(ABC):
    """Abstraction for knowledge source connectors (Google Drive, GitHub, etc.)."""

    @abstractmethod
    def fetch_documents(self, org_id: str, since: Optional[str] = None) -> list[Document]:
        """Fetch documents from the source, optionally filtered by update timestamp."""
        ...

    @abstractmethod
    def source_type(self) -> SourceType:
        """Return the SourceType this connector implements."""
        ...
