"""
Dependency injection container.

This is the ONLY file allowed to import from adapters/ and infra/.
All wiring of services, adapters, and configuration happens here.

Implements singleton pattern: one instance of each adapter for app lifetime.
"""

import logging

from adapters.connectors.google_drive import GoogleDriveConnector
from adapters.connectors.github import GitHubConnector
from adapters.outbound.failover_llm import FailoverLLMAdapter
from adapters.outbound.gemini_llm import GeminiLLMAdapter
from adapters.outbound.openai_embed_adapter import OpenAIEmbedAdapter
from adapters.outbound.openai_llm import OpenAILLMAdapter
from adapters.outbound.qdrant_adapter import QdrantAdapter
from adapters.outbound.unstructured_parser import UnstructuredParserAdapter
from infra.config import settings
from services.chunking_service import ChunkingService
from services.ingestion_service import IngestionService
from services.permission_service import PermissionService
from services.query_service import QueryService
from services.translation_service import TranslationService

logger = logging.getLogger(__name__)

# Module-level singleton container
_container = None


def build_connector(connector_type: str, credentials: dict, org_id: str):
    """
    Factory function to build connectors dynamically.

    Args:
        connector_type: "google_drive" or "github"
        credentials: dict with connector-specific credentials
        org_id: Organization ID for tenant isolation

    Returns:
        Connector instance or None if credentials invalid

    Examples:
        build_connector("github", {"personal_access_token": settings.github_pat, "repos": ["org/repo"]}, org_id)
        build_connector("google_drive", {"access_token": "...", "refresh_token": "...", ...}, org_id)
    """
    try:
        if connector_type == "github":
            return GitHubConnector(credentials, org_id)
        elif connector_type == "google_drive":
            return GoogleDriveConnector(credentials, org_id)
        else:
            logger.error(f"[Container] Unknown connector type: {connector_type}")
            return None
    except Exception as e:
        logger.error(f"[Container] Failed to build {connector_type} connector: {e}")
        return None


def build_container() -> dict:
    """
    Build and wire all services and adapters.

    Returns:
        dict with "query_service" and "ingestion_service" ready to use
    """
    logger.info("[Container] building dependency graph")

    # --- Outbound adapters (stateless, reusable) ---

    # Embedding provider (OpenAI)
    embedding_provider = OpenAIEmbedAdapter(api_key=settings.openai_api_key)

    # Vector store (Qdrant)
    vector_store = QdrantAdapter(
        api_key=settings.qdrant_api_key,
        url=settings.qdrant_url,
        collection_name=settings.qdrant_collection,
        embedding_dim=embedding_provider.dimensions(),
    )

    # LLM provider (Gemini primary, OpenAI GPT-4o-mini fallback)
    gemini_llm = GeminiLLMAdapter(api_key=settings.google_ai_api_key)
    openai_llm = OpenAILLMAdapter(api_key=settings.openai_api_key)
    llm_provider = FailoverLLMAdapter(primary=gemini_llm, fallback=openai_llm)

    # Document parser (Unstructured)
    document_parser = UnstructuredParserAdapter()

    # --- Domain services (stateless, reusable) ---

    # Chunking service
    chunking_service = ChunkingService()

    # Translation service (with caching)
    translation_service = TranslationService()

    # Permission service (tenant isolation)
    permission_service = PermissionService()

    # --- Main services ---

    # Query service (orchestrates RAG pipeline)
    query_service = QueryService(
        embedding_provider=embedding_provider,
        vector_store=vector_store,
        llm_provider=llm_provider,
        permission_service=permission_service,
        translation_service=translation_service,
    )

    # Ingestion service (fetches → chunks → embeds → stores)
    ingestion_service = IngestionService(
        parser=document_parser,
        chunker=chunking_service,
        embedder=embedding_provider,
        store=vector_store,
    )

    logger.info("[Container] dependency graph built successfully")

    return {
        "query_service": query_service,
        "ingestion_service": ingestion_service,
    }


def get_container() -> dict:
    """
    Get or initialize the singleton container.

    Lazy initialization: container is created on first call.
    All subsequent calls return the same instance.

    Returns:
        dict with "query_service" and "ingestion_service"
    """
    global _container

    if _container is None:
        _container = build_container()

    return _container


def reset_container() -> None:
    """
    Reset the container (for testing only).

    Useful for creating fresh dependencies in tests.
    """
    global _container
    _container = None
    logger.debug("[Container] reset for testing")
