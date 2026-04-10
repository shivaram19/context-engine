"""
Tenant context middleware — sets org_id for RLS on every request.

Extracts org_id from Supabase JWT claims in Authorization header.
If found, sets app.current_org_id in Postgres session (RLS uses this).
If missing, allows request through (RLS will return empty results — safe fail).
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from infra.database import get_connection, set_tenant_context

logger = logging.getLogger(__name__)


class TenantContextMiddleware(BaseHTTPMiddleware):
    """
    Sets tenant context (org_id) in Postgres for every request.

    Extracts org_id from Supabase JWT claims in Authorization header.
    Sets app.current_org_id in session before any DB queries run.

    If org_id is missing: allows request through (RLS returns empty results — safe fail).
    """

    async def dispatch(self, request: Request, call_next):
        """Set tenant context and pass request to next middleware."""
        # Extract JWT claims from request state (set by JWT middleware earlier in chain)
        claims = getattr(request.state, "jwt_claims", {})
        org_id = claims.get("org_id")

        # If org_id found, set it in Postgres session for RLS
        if org_id:
            try:
                conn = await get_connection()
                async with set_tenant_context(conn, org_id):
                    response = await call_next(request)
                await conn.close()
                return response
            except Exception as e:
                logger.error(f"[TenantContextMiddleware] failed to set context for {org_id}: {e}")
                # Continue anyway — request will see no data (safe fail)

        # No org_id — request continues with no tenant context
        # RLS queries return zero rows (safe fail)
        return await call_next(request)
