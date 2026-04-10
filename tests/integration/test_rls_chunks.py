"""
RLS (Row Level Security) integration tests for chunks and queries tables.

Tests that tenant isolation works correctly:
1. Org A cannot see Org B's data
2. Missing context returns empty results (safe fail)

Run: pytest tests/integration/test_rls_chunks.py -v
"""

import uuid
from datetime import datetime, timezone

import pytest
import asyncpg

from infra.database import init_pool, close_pool, set_tenant_context


@pytest.fixture
async def db_pool():
    """Create database connection pool for tests."""
    await init_pool()
    yield
    await close_pool()


@pytest.fixture
async def two_orgs(db_pool):
    """Create two organisations and return their IDs."""
    conn = await asyncpg.connect(
        user="postgres",
        password="postgres",
        database="postgres",
        host="localhost",
        port=5432,
    )

    try:
        org_a = str(uuid.uuid4())
        org_b = str(uuid.uuid4())

        await conn.execute(
            "INSERT INTO organisations (id, name) VALUES ($1, $2), ($3, $4)",
            org_a,
            "Org Alpha",
            org_b,
            "Org Beta",
        )

        yield org_a, org_b

        # Cleanup
        await conn.execute("DELETE FROM organisations WHERE id IN ($1, $2)", org_a, org_b)

    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_chunk_rls_isolation(two_orgs):
    """
    THE MOST IMPORTANT TEST IN THE PROJECT.
    Tenant A must not see Tenant B's data. Ever.

    Test: Insert chunks as Org A, query as Org B, verify zero rows returned.
    """
    org_a, org_b = two_orgs

    conn = await asyncpg.connect(
        user="postgres",
        password="postgres",
        database="postgres",
        host="localhost",
        port=5432,
    )

    try:
        # 1. Create a document in Org A
        doc_id_a = str(uuid.uuid4())
        await conn.execute(
            "SELECT set_config('app.current_org_id', $1, true)",
            org_a,
        )
        await conn.execute(
            """
            INSERT INTO documents (id, org_id, data_source_id, source_url, title,
                                   source_type, authority_score, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            doc_id_a,
            org_a,
            str(uuid.uuid4()),  # dummy data_source_id
            "https://example.com/doc_a",
            "Org A Document",
            "google_drive",
            0.7,
            datetime.now(timezone.utc),
        )

        # 2. Insert 3 chunks as Org A
        chunk_ids_a = [str(uuid.uuid4()) for _ in range(3)]
        for i, chunk_id in enumerate(chunk_ids_a):
            await conn.execute(
                """
                INSERT INTO chunks (id, org_id, document_id, content_text, source_url,
                                   source_type, authority_score, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                chunk_id,
                org_a,
                doc_id_a,
                f"Content {i} from Org A",
                "https://example.com/doc_a",
                "google_drive",
                0.7,
                datetime.now(timezone.utc),
            )

        # 3. Switch to Org B context
        await conn.execute(
            "SELECT set_config('app.current_org_id', $1, true)",
            org_b,
        )

        # 4. Query as Org B
        rows = await conn.fetch("SELECT * FROM chunks")

        # 5. Assert zero rows (RLS working!)
        assert len(rows) == 0, f"RLS FAILURE: Org B can see {len(rows)} chunks from Org A"

    finally:
        # Cleanup
        await conn.execute("SELECT set_config('app.current_org_id', $1, true)", org_a)
        await conn.execute("DELETE FROM chunks WHERE org_id=$1", org_a)
        await conn.execute("DELETE FROM documents WHERE org_id=$1", org_a)
        await conn.close()


@pytest.mark.asyncio
async def test_chunk_rls_no_context_returns_empty(two_orgs):
    """
    If org context is not set, must return zero rows (not all rows, not error).
    This is the fail-safe test — missing context = safe empty result.
    """
    org_a, org_b = two_orgs

    conn = await asyncpg.connect(
        user="postgres",
        password="postgres",
        database="postgres",
        host="localhost",
        port=5432,
    )

    try:
        # 1. Create and insert data as Org A
        doc_id_a = str(uuid.uuid4())
        await conn.execute(
            "SELECT set_config('app.current_org_id', $1, true)",
            org_a,
        )
        await conn.execute(
            """
            INSERT INTO documents (id, org_id, data_source_id, source_url, title,
                                   source_type, authority_score, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            doc_id_a,
            org_a,
            str(uuid.uuid4()),
            "https://example.com/doc_a",
            "Org A Document",
            "google_drive",
            0.7,
            datetime.now(timezone.utc),
        )

        chunk_id = str(uuid.uuid4())
        await conn.execute(
            """
            INSERT INTO chunks (id, org_id, document_id, content_text, source_url,
                               source_type, authority_score, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            chunk_id,
            org_a,
            doc_id_a,
            "Content from Org A",
            "https://example.com/doc_a",
            "google_drive",
            0.7,
            datetime.now(timezone.utc),
        )

        # 2. Clear context (set to empty string)
        await conn.execute(
            "SELECT set_config('app.current_org_id', '', true)"
        )

        # 3. Query with no context
        rows = await conn.fetch("SELECT * FROM chunks")

        # 4. Assert zero rows (safe fail, not error)
        assert len(rows) == 0, f"RLS FAILURE: missing context returns {len(rows)} rows (should be 0)"

    finally:
        # Cleanup
        await conn.execute("SELECT set_config('app.current_org_id', $1, true)", org_a)
        await conn.execute("DELETE FROM chunks WHERE org_id=$1", org_a)
        await conn.execute("DELETE FROM documents WHERE org_id=$1", org_a)
        await conn.close()


@pytest.mark.asyncio
async def test_query_rls_isolation(two_orgs):
    """
    Same RLS isolation test for queries table.
    Org A inserts query records, Org B cannot see them.
    """
    org_a, org_b = two_orgs

    conn = await asyncpg.connect(
        user="postgres",
        password="postgres",
        database="postgres",
        host="localhost",
        port=5432,
    )

    try:
        # 1. Create a user in Org A
        user_id_a = str(uuid.uuid4())
        await conn.execute(
            "SELECT set_config('app.current_org_id', $1, true)",
            org_a,
        )
        await conn.execute(
            """
            INSERT INTO users (id, org_id, email, role)
            VALUES ($1, $2, $3, $4)
            """,
            user_id_a,
            org_a,
            "user@org-a.com",
            "member",
        )

        # 2. Insert 3 queries as Org A
        for i in range(3):
            await conn.execute(
                """
                INSERT INTO queries (org_id, user_id, query_text, response_text, detected_language)
                VALUES ($1, $2, $3, $4, $5)
                """,
                org_a,
                user_id_a,
                f"Query {i} from Org A",
                f"Response {i}",
                "en",
            )

        # 3. Switch to Org B context
        await conn.execute(
            "SELECT set_config('app.current_org_id', $1, true)",
            org_b,
        )

        # 4. Query as Org B
        rows = await conn.fetch("SELECT * FROM queries")

        # 5. Assert zero rows
        assert len(rows) == 0, f"RLS FAILURE: Org B can see {len(rows)} queries from Org A"

    finally:
        # Cleanup
        await conn.execute("SELECT set_config('app.current_org_id', $1, true)", org_a)
        await conn.execute("DELETE FROM queries WHERE org_id=$1", org_a)
        await conn.execute("DELETE FROM users WHERE org_id=$1", org_a)
        await conn.close()


@pytest.mark.asyncio
async def test_documents_rls_isolation(two_orgs):
    """
    Same RLS isolation test for documents table.
    Org A inserts documents, Org B cannot see them.
    """
    org_a, org_b = two_orgs

    conn = await asyncpg.connect(
        user="postgres",
        password="postgres",
        database="postgres",
        host="localhost",
        port=5432,
    )

    try:
        # 1. Create data source in Org A
        ds_id_a = str(uuid.uuid4())
        await conn.execute(
            "SELECT set_config('app.current_org_id', $1, true)",
            org_a,
        )
        await conn.execute(
            """
            INSERT INTO data_sources (id, org_id, source_type, config)
            VALUES ($1, $2, $3, $4)
            """,
            ds_id_a,
            org_a,
            "google_drive",
            '{}',  # empty config for test
        )

        # 2. Insert 3 documents as Org A
        doc_ids_a = [str(uuid.uuid4()) for _ in range(3)]
        for i, doc_id in enumerate(doc_ids_a):
            await conn.execute(
                """
                INSERT INTO documents (id, org_id, data_source_id, source_url, title,
                                       source_type, authority_score, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                doc_id,
                org_a,
                ds_id_a,
                f"https://example.com/doc_{i}",
                f"Org A Document {i}",
                "google_drive",
                0.7,
                datetime.now(timezone.utc),
            )

        # 3. Switch to Org B context
        await conn.execute(
            "SELECT set_config('app.current_org_id', $1, true)",
            org_b,
        )

        # 4. Query as Org B
        rows = await conn.fetch("SELECT * FROM documents")

        # 5. Assert zero rows
        assert len(rows) == 0, f"RLS FAILURE: Org B can see {len(rows)} documents from Org A"

    finally:
        # Cleanup
        await conn.execute("SELECT set_config('app.current_org_id', $1, true)", org_a)
        await conn.execute("DELETE FROM documents WHERE org_id=$1", org_a)
        await conn.execute("DELETE FROM data_sources WHERE org_id=$1", org_a)
        await conn.close()
