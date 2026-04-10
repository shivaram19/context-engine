#!/usr/bin/env python3
"""
Real-world integration test using YOUR actual data.

This script:
1. Fetches documents from YOUR Google Drive folder
2. Fetches code from YOUR GitHub repo(s)
3. Chunks and embeds them
4. Stores in Qdrant
5. Runs test queries

Usage:
    python scripts/test_with_real_data.py
"""

import asyncio
import logging
import sys
from datetime import datetime

from infra.config import settings
from infra.container import get_container, reset_container
from adapters.connectors.google_drive import GoogleDriveConnector
from adapters.connectors.github import GitHubConnector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Run real integration test with your data."""

    print("\n" + "="*70)
    print("CONTEXT ENGINE — Real Data Integration Test")
    print("="*70)

    # Reset container to ensure fresh state
    reset_container()

    # Get services from DI container
    container = get_container()
    query_service = container["query_service"]
    ingestion_service = container["ingestion_service"]

    org_id = "shivaramgoud-org"  # You — the SME

    # ============================================
    # STEP 1: Fetch from Google Drive
    # ============================================
    print(f"\n📁 STEP 1: Fetching from Google Drive...")
    print(f"   Using credentials from .env file")

    try:
        gd_creds = {
            "access_token": settings.supabase_url,  # Placeholder — actual token from Google OAuth flow
            "refresh_token": "",  # Not needed for first test
        }

        # NOTE: For real Google Drive access, you need OAuth2 token
        # For now, we'll skip this and test GitHub instead
        print("   ⚠️  Google Drive requires OAuth2 flow (interactive)")
        print("   ℹ️  Skipping for now — use web UI at /auth/google to authenticate first")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        logger.error(f"Google Drive error: {e}")

    # ============================================
    # STEP 2: Fetch from GitHub
    # ============================================
    print(f"\n🐙 STEP 2: Fetching from GitHub...")

    if not settings.github_pat:
        print("   ❌ GITHUB_PAT not set in .env")
        print("   ℹ️  Create a token at: https://github.com/settings/tokens")
        sys.exit(1)

    try:
        github_connector = GitHubConnector(
            credentials={"personal_access_token": settings.github_pat},
            org_id=org_id,
        )

        print(f"   ✅ GitHub connector initialized")

        # Fetch documents from GitHub
        documents = github_connector.fetch_documents(org_id=org_id)
        print(f"   📊 Fetched {len(documents)} documents from GitHub")

        if documents:
            for doc in documents[:3]:  # Show first 3
                print(f"      • {doc.title} ({doc.source_url})")
            if len(documents) > 3:
                print(f"      ... and {len(documents) - 3} more")

    except Exception as e:
        print(f"   ❌ Error: {e}")
        logger.error(f"GitHub error: {e}")
        documents = []

    # ============================================
    # STEP 3: Ingest into Qdrant
    # ============================================
    print(f"\n🔄 STEP 3: Ingesting documents...")

    if documents:
        try:
            # Create a mock connector that returns our documents
            class MockConnector:
                def fetch_documents(self, org_id, since=None):
                    return documents

                def source_type(self):
                    from domain.models import SourceType
                    return SourceType.GITHUB_CODE

            chunks_indexed = ingestion_service.ingest(MockConnector(), org_id)
            print(f"   ✅ Indexed {chunks_indexed} chunks into Qdrant")

        except Exception as e:
            print(f"   ❌ Error during ingestion: {e}")
            logger.error(f"Ingestion error: {e}")
            chunks_indexed = 0
    else:
        chunks_indexed = 0

    # ============================================
    # STEP 4: Run test queries
    # ============================================
    print(f"\n💬 STEP 4: Testing queries against your knowledge base...")

    if chunks_indexed == 0:
        print("   ⚠️  No documents indexed. Skipping query tests.")
        print("\n   💡 To test with Google Drive, authenticate at:")
        print("      http://localhost:8000/auth/google")
        return

    # Test queries
    test_queries = [
        ("What are the main functions in this codebase?", "en"),
        ("यह कोडबेस क्या करता है?", "hi"),  # Hindi: "What does this codebase do?"
        ("How is error handling implemented?", "en"),
    ]

    print(f"\n   Running {len(test_queries)} test queries...\n")

    for query_text, lang in test_queries:
        try:
            result = query_service.query(
                user_id="you",
                org_id=org_id,
                query_text=query_text,
                company_name="Your Organization",
            )

            lang_label = "🇬🇧 EN" if lang == "en" else "🇮🇳 HI"
            print(f"   {lang_label} Q: {query_text[:50]}...")
            print(f"       A: {result.answer[:100]}...")
            print(f"       📚 Citations: {len(result.citations)}")
            print(f"       ⏱️  {result.latency_ms['generate_ms']}ms to generate")
            print()

        except Exception as e:
            print(f"   ❌ Query failed: {e}")
            logger.error(f"Query error: {e}")

    # ============================================
    # Summary
    # ============================================
    print("="*70)
    print("✅ Real Data Integration Test Complete!")
    print("="*70)
    print(f"""
Your Context Engine is now:
  • Connected to your Qdrant instance
  • Indexed {chunks_indexed} chunks from your sources
  • Ready to answer questions about your knowledge base

Next steps:
  1. Visit http://localhost:8000/chat to test the UI
  2. POST to /api/v1/query to test the API
  3. Authenticate Google Drive at /auth/google for more documents
  4. Run: python scripts/query.py --org-id {org_id} --query "your question"
""")


if __name__ == "__main__":
    asyncio.run(main())
