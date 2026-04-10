"""
Async Postgres connection pool and tenant context management.
This is the ONLY place in the codebase that touches the Postgres connection directly.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg

from infra.config import settings

# Global connection pool instance
_pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool:
    """Initialize the async connection pool."""
    global _pool
    _pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=5,
        max_size=20,
        command_timeout=60,
    )
    return _pool


async def close_pool() -> None:
    """Close the connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def get_connection() -> asyncpg.Connection:
    """Get a connection from the pool."""
    if not _pool:
        raise RuntimeError("Connection pool not initialized. Call init_pool() first.")
    return await _pool.acquire()


@asynccontextmanager
async def set_tenant_context(
    conn: asyncpg.Connection, org_id: str
) -> AsyncGenerator[None, None]:
    """
    Context manager to set tenant context for a connection.
    All subsequent queries use the tenant's org_id for RLS.
    """
    try:
        await conn.execute(
            "SELECT set_config('app.current_org_id', $1, true)",
            org_id,
        )
        yield
    finally:
        # Reset context when done
        await conn.execute("SELECT set_config('app.current_org_id', '', true)")
