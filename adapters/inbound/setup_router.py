"""
Setup and configuration router — web UI for data source setup.
FULLY CONNECTED TO BACKEND SERVICES!

Endpoints:
  GET  /setup                    - Setup wizard UI
  GET  /setup/test               - Testing dashboard UI
  POST /api/setup/test-github    - Test GitHub connection (REAL)
  POST /api/setup/save-config    - Save configuration (REAL)
  POST /api/setup/start-ingestion- Start ingestion pipeline (REAL)
  GET  /api/setup/status         - Check ingestion status (REAL)
  POST /api/v1/query             - Query knowledge base (REAL)
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional
import threading

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from jinja2 import Environment, FileSystemLoader

from adapters.connectors.github import GitHubConnector
from infra.config import settings
from infra.container import get_container, reset_container

logger = logging.getLogger(__name__)

router = APIRouter(tags=["setup"])

# Template directory
TEMPLATES_DIR = Path(__file__).parent / "templates"
jinja_env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

CONFIG_FILE = Path("config.data_sources.json")

# Global state for ingestion tracking
ingestion_state = {
    "status": "idle",  # idle, ingesting, complete, error
    "progress": 0,
    "chunks_indexed": 0,
    "started_at": None,
    "error": None,
}


class DataSourceConfig(BaseModel):
    """Data source configuration."""
    organization_name: str
    github_enabled: bool = False
    github_repos: list[str] = []
    github_exclude_paths: list[str] = []
    google_drive_enabled: bool = False
    google_drive_folders: list[dict] = []


class GitHubTestRequest(BaseModel):
    """Test GitHub connection."""
    repos: list[str]


class TestResponse(BaseModel):
    """Test response."""
    success: bool
    message: str
    count: Optional[int] = None


# ============================================
# UI Pages (HTML)
# ============================================


@router.get("/setup", response_class=HTMLResponse)
async def setup_ui(request: Request):
    """Setup wizard UI."""
    config = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            config = json.load(f)

    template = jinja_env.get_template("setup.html")
    html = template.render(
        request=request,
        config=config,
        has_config=CONFIG_FILE.exists(),
    )
    return HTMLResponse(content=html)


@router.get("/setup/test", response_class=HTMLResponse)
async def test_ui(request: Request):
    """Real data testing UI."""
    if not CONFIG_FILE.exists():
        raise HTTPException(
            status_code=400,
            detail="No data sources configured. Go to /setup first.",
        )

    with open(CONFIG_FILE) as f:
        config = json.load(f)

    template = jinja_env.get_template("test_real_data.html")
    html = template.render(
        request=request,
        config=config,
    )
    return HTMLResponse(content=html)


# ============================================
# API Endpoints — CONNECTED TO BACKEND
# ============================================


@router.post("/setup/api/test-github")
async def test_github_connection(payload: GitHubTestRequest) -> TestResponse:
    """Test GitHub connection and count documents. ✅ REAL"""
    if not settings.github_pat:
        return TestResponse(
            success=False,
            message="GITHUB_PAT not set in .env file",
        )

    try:
        logger.info(f"[TestGitHub] Testing GitHub connection for {len(payload.repos)} repos: {payload.repos}")

        # Create connector WITH repos list
        connector = GitHubConnector(
            credentials={
                "personal_access_token": settings.github_pat,
                "repos": payload.repos,  # Pass the repos list!
            },
            org_id="test-org",
        )

        logger.debug("[TestGitHub] Connector created, fetching documents...")
        docs = connector.fetch_documents(org_id="test-org")
        total_docs = len(docs)

        logger.info(f"[TestGitHub] ✅ Successfully fetched {total_docs} documents from {len(payload.repos)} repos")

        return TestResponse(
            success=True,
            message=f"✅ Connected! Found {total_docs} documents across {len(payload.repos)} repos",
            count=total_docs,
        )

    except Exception as e:
        logger.error(f"[TestGitHub] ❌ GitHub connection failed: {e}", exc_info=True)
        return TestResponse(
            success=False,
            message=f"❌ GitHub connection failed: {str(e)}",
        )


@router.post("/setup/api/save-config")
async def save_config(config: DataSourceConfig) -> dict:
    """Save data source configuration. ✅ REAL"""
    try:
        config_data = {
            "organization": {
                "id": config.organization_name.lower().replace(" ", "-"),
                "name": config.organization_name,
            },
            "github": {
                "enabled": config.github_enabled,
                "repositories": config.github_repos,
                "exclude_paths": config.github_exclude_paths or [
                    ".git",
                    "node_modules",
                    "__pycache__",
                    ".env",
                ],
            },
            "google_drive": {
                "enabled": config.google_drive_enabled,
                "folders": config.google_drive_folders,
            },
        }

        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, f, indent=2)

        logger.info(f"[SetupRouter] Config saved: {config.organization_name}")

        return {
            "success": True,
            "message": "✅ Configuration saved!",
            "config": config_data,
        }

    except Exception as e:
        logger.error(f"[SetupRouter] Failed to save config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/setup/api/config")
async def get_config() -> dict:
    """Get current configuration. ✅ REAL"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


@router.post("/setup/api/start-ingestion")
async def start_ingestion() -> dict:
    """Start real data ingestion pipeline. ✅ REAL"""
    if not CONFIG_FILE.exists():
        raise HTTPException(status_code=400, detail="No config found")

    # Load config
    with open(CONFIG_FILE) as f:
        config = json.load(f)

    # Update state
    ingestion_state["status"] = "ingesting"
    ingestion_state["progress"] = 0
    ingestion_state["chunks_indexed"] = 0
    ingestion_state["error"] = None

    # Run ingestion synchronously so we can see logs
    try:
        logger.info("[Ingestion] ⏳ Starting ingestion...")
        import sys

        # Flush logs immediately
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
        logging.getLogger().addHandler(handler)
        logging.getLogger().setLevel(logging.DEBUG)

        # Reset container to get fresh services
        reset_container()
        container = get_container()
        ingestion_service = container["ingestion_service"]
        org_id = config["organization"]["id"]

        logger.info(f"[Ingestion] org_id: {org_id}")
        logger.debug(f"[Ingestion] config: {config}")

        total_chunks = 0

        # Ingest from GitHub if enabled
        if config["github"]["enabled"] and config["github"]["repositories"]:
            logger.info(f"[Ingestion] 🐙 GitHub enabled with {len(config['github']['repositories'])} repos: {config['github']['repositories']}")
            try:
                github_connector = GitHubConnector(
                    credentials={
                        "personal_access_token": settings.github_pat,
                        "repos": config["github"]["repositories"],
                    },
                    org_id=org_id,
                )
                logger.info(f"[Ingestion] 🔗 GitHub connector created, starting ingest...")
                sys.stdout.flush()  # Force flush

                chunks = ingestion_service.ingest(github_connector, org_id)
                total_chunks += chunks
                logger.info(f"[Ingestion] ✅ GitHub: {chunks} chunks indexed")
            except Exception as e:
                logger.error(f"[Ingestion] ❌ GitHub failed: {e}", exc_info=True)
                ingestion_state["error"] = str(e)
        else:
            logger.warning("[Ingestion] ⚠️  GitHub not enabled or no repos configured")

        ingestion_state["chunks_indexed"] = total_chunks
        ingestion_state["status"] = "complete"
        ingestion_state["progress"] = 100
        logger.info(f"[Ingestion] ✅✅ COMPLETE: {total_chunks} total chunks indexed")

    except Exception as e:
        logger.error(f"[Ingestion] ❌ Fatal error: {e}", exc_info=True)
        ingestion_state["status"] = "error"
        ingestion_state["error"] = str(e)

    return {
        "success": True,
        "message": "🚀 Ingestion started! Check status below...",
        "status": "ingesting",
    }


@router.get("/setup/api/ingestion-status")
async def get_ingestion_status() -> dict:
    """Get ingestion progress. ✅ REAL"""
    return {
        "status": ingestion_state["status"],
        "progress": ingestion_state["progress"],
        "chunks_indexed": ingestion_state["chunks_indexed"],
        "error": ingestion_state["error"],
    }


@router.get("/setup/api/debug/qdrant-info")
async def debug_qdrant_info() -> dict:
    """Debug endpoint: Show what's actually in Qdrant. ✅ REAL"""
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            prefer_grpc=False,
        )

        collection_info = client.get_collection(settings.qdrant_collection)

        # Get a sample of points to see org_ids
        sample_points = client.scroll(
            collection_name=settings.qdrant_collection,
            limit=5,
        )

        org_ids = set()
        for point, _ in sample_points:
            if hasattr(point, 'payload') and point.payload:
                org_ids.add(point.payload.get("org_id", "UNKNOWN"))

        return {
            "total_points": collection_info.points_count,
            "sample_org_ids": list(org_ids),
            "collection_name": settings.qdrant_collection,
        }
    except Exception as e:
        logger.error(f"[DebugQdrant] Error: {e}", exc_info=True)
        return {"error": str(e)}


@router.post("/api/v1/query")
async def query_knowledge_base(request: Request) -> dict:
    """Query knowledge base with real LLM. ✅ REAL"""
    body = await request.json()

    query_text = body.get("query", "")
    company_name = body.get("company_name", "Your Organization")

    if not query_text:
        raise HTTPException(status_code=400, detail="Query text required")

    # Load org_id from config file (the configured organization context)
    if not CONFIG_FILE.exists():
        raise HTTPException(status_code=400, detail="No configuration found. Go to /setup first.")

    with open(CONFIG_FILE) as f:
        config = json.load(f)
    org_id = config["organization"]["id"]

    try:
        logger.info(f"[SetupRouter Query] Incoming: query='{query_text[:100]}...', org_id={org_id} (from config)")

        # Get services
        container = get_container()
        query_service = container["query_service"]

        # Run query
        result = query_service.query(
            user_id="web-user",
            org_id=org_id,
            query_text=query_text,
            company_name=company_name,
        )

        logger.debug(f"[SetupRouter Query] Result obtained: answer_len={len(result.answer)}, latency_keys={list(result.latency_ms.keys())}")

        response_dict = {
            "answer": result.answer,
            "citations": result.citations,
            "response_language": result.response_language,
            "latency_ms": result.latency_ms,
        }
        logger.debug(f"[SetupRouter Query] Returning: {list(response_dict.keys())}")
        return response_dict

    except Exception as e:
        logger.error(f"[SetupRouter Query] Failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
