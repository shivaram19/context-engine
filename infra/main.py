"""
FastAPI application entry point.

Initializes:
- Database connection pool
- Dependency injection container
- Middleware (JWT, tenant context)
- Routers (REST API)
"""

import logging

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from adapters.inbound.rest_router import router as rest_router
from adapters.inbound.whatsapp_handler import router as whatsapp_router, close_wati_client
from adapters.inbound.admin_router import router as admin_router
from adapters.inbound.setup_router import router as setup_router
from infra.config import settings
from infra.database import init_pool, close_pool
from infra.tenant_middleware import TenantContextMiddleware

logger = logging.getLogger(__name__)

# Initialize Sentry for production error tracking
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,  # 10% of requests traced
        environment=settings.environment,
    )
    logger.info("[Main] Sentry initialized")

# Create FastAPI app
app = FastAPI(
    title="Context Engine",
    description="AI-native organisational context engine for SMEs",
    version="0.1.0",
)

# --- Middleware ---

# CORS middleware (allow all origins for MVP)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tenant context middleware (sets org_id for RLS)
app.add_middleware(TenantContextMiddleware)

# JWT middleware would go here (e.g., python-jose for Supabase token verification)
# For MVP: assumes request.state.jwt_claims is set by external service or placeholder

# --- Routers ---

app.include_router(rest_router)
app.include_router(whatsapp_router)
app.include_router(admin_router)
app.include_router(setup_router)


# --- Startup/shutdown ---

@app.on_event("startup")
async def startup_event():
    """Initialize database pool and container on app startup."""
    logger.info("[Main] starting up...")

    try:
        # Initialize database connection pool
        await init_pool()
        logger.info("[Main] database pool initialized")

        # Initialize dependency injection container
        from infra.container import get_container
        container = get_container()
        logger.info(f"[Main] DI container initialized with {len(container)} services")

    except Exception as e:
        logger.error(f"[Main] startup failed: {e}")
        # In development, allow graceful failure for testing static routes like /chat
        if settings.environment != "development":
            raise
        logger.warning("[Main] continuing in development mode with degraded functionality")


@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on app shutdown."""
    logger.info("[Main] shutting down...")

    try:
        # Close WATI client
        await close_wati_client()

        # Close database connection pool
        await close_pool()
        logger.info("[Main] database pool closed")

    except Exception as e:
        logger.error(f"[Main] shutdown error: {e}")


# --- Health check endpoints ---

@app.get("/health")
async def health():
    """Health check endpoint for container orchestration."""
    return {
        "status": "ok",
        "environment": settings.environment,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Context Engine API"}


if __name__ == "__main__":
    import uvicorn

    # Run with: uvicorn infra.main:app --host 0.0.0.0 --port 8000 --reload
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
    )
