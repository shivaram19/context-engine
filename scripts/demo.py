#!/usr/bin/env python3
"""
End-to-end smoke test: ingest documents and query the knowledge base.

Steps:
1. Create test organisation and user
2. Connect Google Drive (requires GOOGLE_DRIVE_CREDENTIALS_JSON in .env)
3. Ingest documents
4. Run English and Hindi queries
5. Print results with latency breakdown

Run: python scripts/demo.py
"""

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone

# Set up logging before imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters.connectors.google_drive import GoogleDriveConnector
from infra.config import settings
from infra.database import init_pool, close_pool
from infra.container import get_container


async def main():
    """Run the end-to-end demo."""
    logger.info("=" * 80)
    logger.info("Context Engine — End-to-End Demo")
    logger.info("=" * 80)

    await init_pool()

    try:
        # Step 1: Create test organisation and user
        logger.info("\n[Step 1] Creating test organisation and user...")
        org_id, user_id = await setup_test_org()
        logger.info(f"✓ Created org_id={org_id}, user_id={user_id}")

        # Step 2: Connect Google Drive
        logger.info("\n[Step 2] Connecting Google Drive...")
        connector = await setup_google_drive()
        logger.info("✓ Google Drive connected")

        # Step 3: Ingest documents
        logger.info("\n[Step 3] Ingesting documents...")
        chunks_indexed, docs_count = await ingest_documents(org_id, connector)
        logger.info(f"✓ Indexed {chunks_indexed} chunks from {docs_count} documents")

        if chunks_indexed == 0:
            logger.warning("⚠ No documents ingested. Check Google Drive credentials and document access.")
            return

        # Step 4: Run queries
        logger.info("\n[Step 4] Running queries...")
        await run_demo_queries(org_id, user_id)

        logger.info("\n" + "=" * 80)
        logger.info("✓ Demo completed successfully!")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"✗ Demo failed: {e}", exc_info=True)
        sys.exit(1)

    finally:
        await close_pool()


async def setup_test_org() -> tuple:
    """
    Create test organisation and user in database.

    Returns: (org_id, user_id)
    """
    import asyncpg

    conn = await asyncpg.connect(
        dsn=settings.database_url,
    )

    try:
        org_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())

        # Create organisation
        await conn.execute(
            "INSERT INTO organisations (id, name) VALUES ($1, $2)",
            org_id,
            "Demo Organisation",
        )

        # Create user with WhatsApp phone (mock)
        await conn.execute(
            """
            INSERT INTO users (id, org_id, email, whatsapp_phone, role)
            VALUES ($1, $2, $3, $4, $5)
            """,
            user_id,
            org_id,
            "demo@example.com",
            "+1234567890",
            "admin",
        )

        return org_id, user_id

    finally:
        await conn.close()


async def setup_google_drive() -> GoogleDriveConnector:
    """
    Create Google Drive connector with test credentials.

    Credentials expected in environment:
    - GOOGLE_AI_API_KEY
    - And Google Drive OAuth credentials
    """
    # For demo, read credentials from .env or environment
    # In production, this would come from the database (data_sources table)

    credentials = {
        "access_token": os.getenv("GOOGLE_DRIVE_ACCESS_TOKEN", ""),
        "refresh_token": os.getenv("GOOGLE_DRIVE_REFRESH_TOKEN", ""),
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
    }

    # Check if credentials are available
    if not any(credentials.values()):
        raise ValueError(
            "Google Drive credentials not found in environment.\n"
            "Please set: GOOGLE_DRIVE_ACCESS_TOKEN, GOOGLE_DRIVE_REFRESH_TOKEN, "
            "GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET"
        )

    connector = GoogleDriveConnector(
        credentials=credentials,
        org_id="demo-org",  # Temporary, will be replaced with actual org_id
    )

    return connector


async def ingest_documents(org_id: str, connector: GoogleDriveConnector) -> tuple:
    """
    Ingest documents from Google Drive.

    Returns: (chunks_indexed, documents_count)
    """
    container = get_container()
    ingestion_service = container["ingestion_service"]

    # Re-initialize connector with correct org_id
    connector._org_id = org_id

    chunks_indexed = ingestion_service.ingest(
        connector=connector,
        org_id=org_id,
    )

    # Count documents
    import asyncpg
    conn = await asyncpg.connect(dsn=settings.database_url)
    try:
        doc_count = await conn.fetchval(
            "SELECT COUNT(*) FROM documents WHERE org_id=$1",
            org_id,
        )
    finally:
        await conn.close()

    return chunks_indexed, doc_count


async def run_demo_queries(org_id: str, user_id: str) -> None:
    """
    Run demo queries in English and Hindi.
    """
    container = get_container()
    query_service = container["query_service"]

    queries = [
        {
            "lang": "EN",
            "text": "What is the main topic of our documents?",
            "lang_code": "en",
        },
        {
            "lang": "HI",
            "text": "हमारी documents किस बारे में हैं?",
            "lang_code": "hi",
        },
    ]

    for q in queries:
        logger.info(f"\n[{q['lang']} Query] {q['text']}")

        result = query_service.query(
            user_id=user_id,
            org_id=org_id,
            query_text=q["text"],
            company_name="Demo Company",
        )

        # Print answer
        logger.info(f"\nAnswer:\n{result.answer}")

        # Print citations
        if result.citations:
            logger.info("\nCitations:")
            for i, citation in enumerate(result.citations, 1):
                logger.info(f"  {i}. {citation.get('title', 'Unknown')}")
                logger.info(f"     {citation.get('url', 'N/A')}")
        else:
            logger.info("\nCitations: None")

        # Print latency breakdown
        latency = result.latency_ms
        logger.info(
            f"\nLatency (ms): detect={latency.get('detect_ms', 0)} "
            f"translate={latency.get('translate_ms', 0)} "
            f"embed={latency.get('embed_ms', 0)} "
            f"retrieve={latency.get('retrieve_ms', 0)} "
            f"generate={latency.get('generate_ms', 0)}"
        )
        logger.info(f"Response Language: {result.response_language}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nDemo interrupted by user")
        sys.exit(0)
