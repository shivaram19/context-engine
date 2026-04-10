"""
Unstructured document parser adapter.
Implements DocumentParser port using unstructured library.
Extracts clean text from PDF, DOCX, HTML, Markdown, plain text.
"""

import logging
from io import BytesIO

from ports.document_parser import DocumentParser

logger = logging.getLogger(__name__)


class UnstructuredParserAdapter(DocumentParser):
    """
    Implements DocumentParser using unstructured library.
    Handles: PDF, DOCX, plain text, HTML, Markdown.
    Returns empty string (not exception) for unsupported types.
    """

    # Supported MIME types
    SUPPORTED_TYPES = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "text/plain": "txt",
        "text/html": "html",
        "text/markdown": "md",
        "text/x-markdown": "md",
    }

    def parse(self, raw_content: bytes, mime_type: str) -> str:
        """
        Parse raw document bytes into clean text.
        Supports PDF, DOCX, HTML, Markdown, plain text.
        Returns empty string for unsupported types.
        """
        if not raw_content:
            return ""

        # Check if MIME type is supported
        if mime_type not in self.SUPPORTED_TYPES:
            logger.warning(
                f"[UnstructuredParserAdapter] Unsupported MIME type: {mime_type}. Returning empty string."
            )
            return ""

        try:
            from unstructured.partition.auto import partition

            # Create BytesIO object for unstructured
            file_obj = BytesIO(raw_content)

            # Auto-detect and partition based on MIME type
            elements = partition(file=file_obj, content_type=mime_type)

            # Extract text from elements
            text_parts = [elem.text for elem in elements if hasattr(elem, "text") and elem.text]
            clean_text = "\n".join(text_parts)

            logger.debug(
                f"[UnstructuredParserAdapter] parsed {len(elements)} elements, {len(clean_text)} chars"
            )
            return clean_text

        except ImportError:
            logger.error("[UnstructuredParserAdapter] unstructured library not installed")
            return ""
        except Exception as e:
            logger.error(f"[UnstructuredParserAdapter] parse failed for {mime_type}: {e}")
            return ""
