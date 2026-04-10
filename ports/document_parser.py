"""
Document parser port — abstract interface for parsing raw content into text.
"""

from abc import ABC, abstractmethod


class DocumentParser(ABC):
    """Abstraction for document parsers (PDF, DOCX, HTML, etc.)."""

    @abstractmethod
    def parse(self, raw_content: bytes, mime_type: str) -> str:
        """Parse raw bytes into plain text."""
        ...
