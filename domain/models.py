"""
Core domain models for the Context Engine.

Pure dataclasses with zero external dependencies. Business logic only.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class SourceType(Enum):
    """Types of knowledge sources."""
    GOOGLE_DRIVE = "google_drive"
    GITHUB_PR = "github_pr"
    GITHUB_CODE = "github_code"
    SLACK = "slack"
    NOTION = "notion"


class Language(Enum):
    """Supported languages."""
    ENGLISH = "en"
    HINDI = "hi"
    TAMIL = "ta"
    MARATHI = "mr"
    BENGALI = "bn"


@dataclass
class Document:
    """A document from a connected knowledge source."""
    id: str
    org_id: str
    source_type: SourceType
    source_url: str
    title: str
    content: str
    authority_score: float  # 1.0=code, 0.9=pr, 0.7=doc, 0.5=chat
    updated_at: datetime
    language: Language = Language.ENGLISH


@dataclass
class Chunk:
    """A chunk of a document, ready for embedding and retrieval."""
    id: str
    document_id: str
    org_id: str
    content_text: str
    source_url: str
    source_type: SourceType
    authority_score: float
    updated_at: datetime
    is_stale: bool = False
    embedding: Optional[list[float]] = field(default=None, repr=False)


@dataclass
class QueryResult:
    """Result of a query including answer, citations, and performance metrics."""
    answer: str
    citations: list[dict]  # [{title, url, source_type, updated_at}]
    response_language: str
    latency_ms: dict  # {detect_ms, translate_ms, embed_ms, retrieve_ms, generate_ms}
    error: Optional[str] = None
