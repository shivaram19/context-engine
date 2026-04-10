"""
Chunking service — split documents into chunks.

Single responsibility: split a Document into Chunks.
Strategy selected by Document.source_type — callers never choose the strategy.

Uses: domain.models, chonkie (behind this service, not exposed elsewhere)
Zero imports from adapters/ or infra/
"""

import re
import uuid

from domain.models import Chunk, Document, SourceType


class ChunkingService:
    """
    Split a Document into semantically meaningful Chunks.
    Strategy selection is automatic based on source_type.
    """

    _PROSE_CHUNK_SIZE = 400  # tokens
    _CODE_CHUNK_SIZE = 300  # tokens — smaller for code
    _CONVO_WINDOW_SIZE = 10  # messages per group

    def chunk(self, document: Document) -> list[Chunk]:
        """
        Split a document into chunks using the appropriate strategy.
        Returns list of Chunks with all fields populated from the Document.
        """
        strategy = self._select_strategy(document.source_type)
        raw_chunks = strategy(document.content)

        return [
            Chunk(
                id=str(uuid.uuid4()),
                document_id=document.id,
                org_id=document.org_id,
                content_text=text,
                source_url=document.source_url,
                source_type=document.source_type,
                authority_score=document.authority_score,
                updated_at=document.updated_at,
            )
            for text in raw_chunks
            if text.strip()
        ]

    def _select_strategy(self, source_type: SourceType):
        """Select chunking strategy based on source type."""
        strategies = {
            SourceType.GOOGLE_DRIVE: self._chunk_prose,
            SourceType.GITHUB_PR: self._chunk_prose,
            SourceType.GITHUB_CODE: self._chunk_code,
            SourceType.SLACK: self._chunk_conversation,
            SourceType.NOTION: self._chunk_prose,
        }
        return strategies.get(source_type, self._chunk_prose)

    def _chunk_prose(self, text: str) -> list[str]:
        """
        Chunk prose documents using semantic chunking.
        Target: ~400 tokens per chunk (approximately 300-500 words).
        """
        try:
            from chonkie import SemanticChunker

            chunker = SemanticChunker(chunk_size=self._PROSE_CHUNK_SIZE)
            return [c.text for c in chunker.chunk(text)]
        except ImportError:
            # Fallback: split on paragraphs (double newlines)
            paragraphs = text.split("\n\n")
            return [p.strip() for p in paragraphs if p.strip()]

    def _chunk_code(self, text: str) -> list[str]:
        """
        Chunk code by function/class boundaries.
        Splits on lines that start with def, class, function, const, export.
        """
        # Split on function/class definitions
        boundaries = re.split(
            r"\n(?=(?:def |class |function |const |export |async ))",
            text,
        )
        return [b.strip() for b in boundaries if b.strip()]

    def _chunk_conversation(self, text: str) -> list[str]:
        """
        Chunk conversations by message groups.
        Groups messages into windows of ~10 messages.
        """
        lines = text.strip().split("\n")
        groups = [
            "\n".join(lines[i : i + self._CONVO_WINDOW_SIZE])
            for i in range(0, len(lines), self._CONVO_WINDOW_SIZE)
        ]
        return [g for g in groups if g.strip()]
