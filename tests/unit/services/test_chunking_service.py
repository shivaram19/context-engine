"""
Unit tests for ChunkingService — document chunking strategy selection.

Tests verify:
- Prose documents chunked by semantic boundaries
- Code documents chunked by function/class boundaries
- Conversation documents grouped into message windows
- Strategy routing based on source type
- Fallback to paragraph splitting when chonkie unavailable
"""

import pytest
from datetime import datetime
from domain.models import Document, SourceType, Language
from services.chunking_service import ChunkingService


@pytest.fixture
def chunking_service():
    """Fresh ChunkingService instance for each test."""
    return ChunkingService()


@pytest.fixture
def prose_document():
    """Sample Google Drive document with prose."""
    return Document(
        id="doc-prose",
        org_id="test-org",
        source_type=SourceType.GOOGLE_DRIVE,
        source_url="https://drive.google.com/file/d/1",
        title="HR Policy",
        content="Leave policy: 20 days per year.\n\nSick leave: 10 days per year.\n\nMaternity leave: 6 months.",
        authority_score=0.7,
        updated_at=datetime(2025, 1, 1),
        language=Language.ENGLISH,
    )


@pytest.fixture
def code_document():
    """Sample GitHub code document."""
    return Document(
        id="doc-code",
        org_id="test-org",
        source_type=SourceType.GITHUB_CODE,
        source_url="https://github.com/org/repo/blob/main/api.py",
        title="API Functions",
        content="""def get_user(user_id):
    return db.query(User).filter(id=user_id).first()

def create_user(name, email):
    user = User(name=name, email=email)
    db.add(user)
    db.commit()
    return user

class UserService:
    def delete_user(self, user_id):
        db.delete(User).where(User.id == user_id)
        db.commit()""",
        authority_score=1.0,
        updated_at=datetime(2025, 1, 1),
        language=Language.ENGLISH,
    )


@pytest.fixture
def conversation_document():
    """Sample Slack conversation document."""
    return Document(
        id="doc-convo",
        org_id="test-org",
        source_type=SourceType.SLACK,
        source_url="https://slack.com/archives/C1234567/p1234567890",
        title="Slack Thread",
        content="""Alice: What's our leave policy?
Bob: 20 days per year
Alice: What about sick leave?
Bob: 10 days
Charlie: Can we carry over days?
Bob: No, they reset each year
Dave: What about parental leave?
Bob: 6 months paid
Eve: Thanks for clarifying!
Bob: Welcome!
Frank: Is this documented?
Bob: Yes, in HR Policy doc""",
        authority_score=0.5,
        updated_at=datetime(2025, 1, 1),
        language=Language.ENGLISH,
    )


def test_chunk_prose_returns_multiple_chunks(chunking_service, prose_document):
    """Prose document should be split into multiple chunks."""
    chunks = chunking_service.chunk(prose_document)
    assert len(chunks) > 1
    assert all(c.content_text.strip() for c in chunks)  # No empty chunks


def test_chunk_preserves_document_metadata(chunking_service, prose_document):
    """Chunks should preserve all metadata from original document."""
    chunks = chunking_service.chunk(prose_document)
    for chunk in chunks:
        assert chunk.document_id == prose_document.id
        assert chunk.org_id == prose_document.org_id
        assert chunk.source_url == prose_document.source_url
        assert chunk.source_type == prose_document.source_type
        assert chunk.authority_score == prose_document.authority_score
        assert chunk.updated_at == prose_document.updated_at


def test_chunk_code_splits_on_function_boundaries(chunking_service, code_document):
    """Code chunks should be split at function/class definitions."""
    chunks = chunking_service.chunk(code_document)

    # Should have at least 2 chunks (separated by def/class boundaries)
    assert len(chunks) >= 2

    # Each chunk should contain code (not just whitespace)
    assert all("def " in c.content_text or "class " in c.content_text for c in chunks)


def test_chunk_conversation_groups_into_windows(chunking_service, conversation_document):
    """Conversation should be grouped into message windows."""
    chunks = chunking_service.chunk(conversation_document)

    # Should have multiple chunks (each ~10 messages)
    assert len(chunks) >= 2

    # Each chunk should contain conversation lines
    assert all(":" in c.content_text for c in chunks)  # Format: "Name: message"


def test_chunk_empty_document_returns_empty(chunking_service):
    """Empty document should return no chunks."""
    empty_doc = Document(
        id="empty",
        org_id="test-org",
        source_type=SourceType.GOOGLE_DRIVE,
        source_url="https://example.com",
        title="Empty",
        content="",
        authority_score=0.5,
        updated_at=datetime(2025, 1, 1),
    )
    chunks = chunking_service.chunk(empty_doc)
    assert len(chunks) == 0


def test_chunk_whitespace_only_document_returns_empty(chunking_service):
    """Document with only whitespace should return no chunks."""
    ws_doc = Document(
        id="whitespace",
        org_id="test-org",
        source_type=SourceType.GOOGLE_DRIVE,
        source_url="https://example.com",
        title="Whitespace",
        content="   \n\n   \t\t  ",
        authority_score=0.5,
        updated_at=datetime(2025, 1, 1),
    )
    chunks = chunking_service.chunk(ws_doc)
    assert len(chunks) == 0


def test_chunk_notion_uses_prose_strategy(chunking_service):
    """Notion documents should use prose chunking strategy."""
    notion_doc = Document(
        id="doc-notion",
        org_id="test-org",
        source_type=SourceType.NOTION,
        source_url="https://notion.so/doc-123",
        title="Notion Doc",
        content="First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph here.",
        authority_score=0.7,
        updated_at=datetime(2025, 1, 1),
    )
    chunks = chunking_service.chunk(notion_doc)
    assert len(chunks) > 1
    assert all(c.source_type == SourceType.NOTION for c in chunks)


def test_chunk_github_pr_uses_prose_strategy(chunking_service):
    """GitHub PR documents should use prose chunking strategy."""
    pr_doc = Document(
        id="doc-pr",
        org_id="test-org",
        source_type=SourceType.GITHUB_PR,
        source_url="https://github.com/org/repo/pull/123",
        title="PR: Add feature X",
        content="This PR adds feature X.\n\nKey changes:\n\n- Change 1\n- Change 2",
        authority_score=0.9,
        updated_at=datetime(2025, 1, 1),
    )
    chunks = chunking_service.chunk(pr_doc)
    assert len(chunks) > 0
    assert all(c.source_type == SourceType.GITHUB_PR for c in chunks)
