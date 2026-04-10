"""
Canonical test fixtures used across all tests.

This is the single source of truth for mock data. Tests should import
from this module rather than creating their own fixtures.
"""

from datetime import datetime
from domain.models import Chunk, Document, QueryResult, SourceType, Language

# Mock identifiers
MOCK_ORG_ID = "aaaa-0000-bbbb-1111"
MOCK_USER_ID = "user-dev-001"
MOCK_DOC_ID = "doc-001"
MOCK_CHUNK_ID = "chunk-001"

# Mock documents
MOCK_DOCUMENTS = [
    Document(
        id="d1",
        org_id=MOCK_ORG_ID,
        source_type=SourceType.GOOGLE_DRIVE,
        source_url="https://drive.google.com/file/d/1",
        title="HR Policy 2025",
        content="Leave policy: 20 days per year. Sick leave: 10 days per year.",
        authority_score=0.7,
        updated_at=datetime(2025, 1, 1),
        language=Language.ENGLISH,
    ),
    Document(
        id="d2",
        org_id=MOCK_ORG_ID,
        source_type=SourceType.GITHUB_CODE,
        source_url="https://github.com/org/repo/blob/main/api.py",
        title="API Implementation",
        content="def get_user(user_id): return db.query(User).filter(id=user_id).first()",
        authority_score=1.0,
        updated_at=datetime(2025, 1, 15),
        language=Language.ENGLISH,
    ),
]

# Mock chunks (with embeddings)
MOCK_CHUNKS = [
    Chunk(
        id="c1",
        document_id="d1",
        org_id=MOCK_ORG_ID,
        content_text="Leave policy: 20 days per year",
        source_url="https://drive.google.com/file/d/1",
        source_type=SourceType.GOOGLE_DRIVE,
        authority_score=0.7,
        updated_at=datetime(2025, 1, 1),
        is_stale=False,
        embedding=[0.1] * 1536,
    ),
    Chunk(
        id="c2",
        document_id="d1",
        org_id=MOCK_ORG_ID,
        content_text="Sick leave: 10 days per year",
        source_url="https://drive.google.com/file/d/1",
        source_type=SourceType.GOOGLE_DRIVE,
        authority_score=0.7,
        updated_at=datetime(2025, 1, 1),
        is_stale=False,
        embedding=[0.2] * 1536,
    ),
    Chunk(
        id="c3",
        document_id="d2",
        org_id=MOCK_ORG_ID,
        content_text="def get_user(user_id): return db.query(User).filter(id=user_id).first()",
        source_url="https://github.com/org/repo/blob/main/api.py",
        source_type=SourceType.GITHUB_CODE,
        authority_score=1.0,
        updated_at=datetime(2025, 1, 15),
        is_stale=False,
        embedding=[0.3] * 1536,
    ),
]

# Mock chunk from different org (for permission testing)
MOCK_CHUNK_WRONG_ORG = Chunk(
    id="c-wrong-org",
    document_id="d-wrong-org",
    org_id="zzzz-9999-xxxx-8888",
    content_text="Secret data from another org",
    source_url="https://example.com/secret",
    source_type=SourceType.GOOGLE_DRIVE,
    authority_score=0.9,
    updated_at=datetime(2025, 1, 1),
    is_stale=False,
    embedding=[0.5] * 1536,
)

# Mock LLM response
MOCK_LLM_ANSWER = "Your leave policy allows 20 days per year for regular leave and 10 days for sick leave."

# Mock query result
MOCK_QUERY_RESULT = QueryResult(
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

# Mock embedding (1536-dim OpenAI text-embedding-3-small)
MOCK_EMBEDDING = [0.123] * 1536
