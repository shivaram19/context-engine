"""
REST API router — HTTP endpoints for the Context Engine.

POST /api/v1/query - process a user query
GET /health - health check

All endpoints require Supabase JWT authentication.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from domain.models import QueryResult
from infra.config import settings
from infra.container import get_container
from infra.database import get_connection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["queries"])


class QueryRequest(BaseModel):
    """Request body for query endpoint."""
    query: str
    org_id: Optional[str] = None  # Optional — defaults to configured org_id
    company_name: str = "your company"


class QueryResponse(BaseModel):
    """Response body for query endpoint."""
    answer: str
    citations: list[dict]
    response_language: str
    latency_ms: dict


@router.post("/query", response_model=QueryResponse)
async def query(request_body: QueryRequest, http_request: Request):
    """
    Process a user query and return a cited answer.

    Args:
        request_body: QueryRequest with query text, optional org_id, company_name
        http_request: FastAPI request for JWT extraction

    Returns:
        QueryResponse with answer, citations, language, latency breakdown
    """
    # DEV ONLY — remove before production deploy
    if settings.environment == "development":
        user_id = "dev-user"
    else:
        user_id = await get_current_user_id(http_request)

    try:
        # If org_id not provided, load from config file
        org_id = request_body.org_id
        if not org_id:
            config_file = Path("config.data_sources.json")
            if config_file.exists():
                with open(config_file) as f:
                    config = json.load(f)
                org_id = config.get("organization", {}).get("id", "default-org")
                logger.info(f"[QueryRouter] org_id not in request, loaded from config: {org_id}")
            else:
                logger.warning("[QueryRouter] org_id not in request and no config file found, using default")
                org_id = "default-org"

        logger.debug(f"[QueryRouter] Incoming query: {request_body.query[:100]}... for org {org_id}")

        # Get query service from container
        container = get_container()
        query_service = container["query_service"]

        # Process query
        result: QueryResult = query_service.query(
            user_id=user_id,
            org_id=org_id,
            query_text=request_body.query,
            company_name=request_body.company_name,
        )

        logger.debug(f"[QueryRouter] Query result: answer_len={len(result.answer)}, citations={len(result.citations)}, latency_keys={list(result.latency_ms.keys())}")

        # Log query asynchronously (fire and forget — don't block response)
        asyncio.create_task(log_query_async(user_id, org_id, request_body.query, result))

        # Return response
        response = QueryResponse(
            answer=result.answer,
            citations=result.citations,
            response_language=result.response_language,
            latency_ms=result.latency_ms,
        )
        logger.debug(f"[QueryRouter] Returning response with latency_ms: {response.latency_ms}")
        return response

    except Exception as e:
        logger.error(f"[QueryRouter] query failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process query. Please try again.",
        )


@router.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def log_query_async(user_id: str, org_id: str, query_text: str, result: QueryResult) -> None:
    """
    Log query to database asynchronously (fire and forget).

    Does not block the response. Errors are logged but not raised.
    """
    try:
        conn = await get_connection()

        # Insert into queries table
        await conn.execute(
            """
            INSERT INTO queries (org_id, user_id, query_text, response_text, detected_language, citations, latency_ms)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            org_id,
            user_id,
            query_text,
            result.answer,
            result.response_language,
            result.citations,  # Will be stored as JSONB
            result.latency_ms,   # Will be stored as JSONB
        )

        await conn.close()
        logger.debug(f"[QueryRouter] logged query for user {user_id}")

    except Exception as e:
        # Development: queries table might not exist. Don't clutter logs.
        logger.debug(f"[QueryRouter] could not persist query log: {e}")
        # Don't raise — logging failure should not affect user response


async def get_current_user_id(request) -> str:
    """
    Extract user_id from JWT claims.

    Expects request.state.jwt_claims (set by JWT middleware).
    Returns user_id or raises 401.
    """
    claims = getattr(request.state, "jwt_claims", {})
    user_id = claims.get("sub")  # Supabase JWT uses 'sub' for user ID

    if not user_id:
        logger.warning("[QueryRouter] missing user_id in JWT claims")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid JWT",
        )

    return user_id
