"""
Simple Postgres-backed job queue for document ingestion.

No Celery, no Redis. Jobs are stored in the ingestion_jobs table.
Worker loop runs as a separate process, polls every 10 seconds.

Run as: python -m infra.job_queue
"""

import asyncio
import json
import logging
from datetime import datetime

import asyncpg

from domain.models import SourceType
from infra.config import settings
from infra.database import init_pool, close_pool, set_tenant_context, get_connection
from infra.container import get_container

logger = logging.getLogger(__name__)

# Poll interval in seconds
POLL_INTERVAL = 10


async def enqueue_job(org_id: str, data_source_id: str) -> str:
    """
    Enqueue an ingestion job.

    Args:
        org_id: Organization ID
        data_source_id: Data source ID to ingest from

    Returns:
        Job ID
    """
    conn = await get_connection()

    try:
        job_id = await conn.fetchval(
            """
            INSERT INTO ingestion_jobs (org_id, data_source_id, status)
            VALUES ($1, $2, 'pending')
            RETURNING id
            """,
            org_id,
            data_source_id,
        )
        logger.info(f"[JobQueue] enqueued job {job_id} for org_id={org_id}, data_source_id={data_source_id}")
        return str(job_id)

    finally:
        await conn.close()


async def worker_loop() -> None:
    """
    Worker loop — polls for pending jobs and processes them.

    Runs as infinite loop, checking every 10 seconds.
    Processes one job at a time (SKIP LOCKED for concurrency safety).
    """
    logger.info("[JobQueue] worker starting...")

    await init_pool()

    try:
        while True:
            try:
                job = await fetch_pending_job()

                if job:
                    job_id, org_id, data_source_id = job
                    await process_job(job_id, org_id, data_source_id)
                else:
                    logger.debug("[JobQueue] no pending jobs")

                # Wait before polling again
                await asyncio.sleep(POLL_INTERVAL)

            except Exception as e:
                logger.error(f"[JobQueue] worker loop error: {e}")
                # Continue polling despite errors
                await asyncio.sleep(POLL_INTERVAL)

    finally:
        await close_pool()
        logger.info("[JobQueue] worker stopped")


async def fetch_pending_job() -> tuple | None:
    """
    Fetch the next pending job.

    Uses SELECT FOR UPDATE SKIP LOCKED for safe concurrent processing.

    Returns (job_id, org_id, data_source_id) or None
    """
    conn = await get_connection()

    try:
        job = await conn.fetchrow(
            """
            SELECT id, org_id, data_source_id
            FROM ingestion_jobs
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
            """
        )

        return tuple(job) if job else None

    finally:
        await conn.close()


async def process_job(job_id: str, org_id: str, data_source_id: str) -> None:
    """
    Process an ingestion job.

    Updates job status: pending → running → done/failed
    """
    logger.info(f"[JobQueue] processing job {job_id} for org_id={org_id}")

    conn = await get_connection()

    try:
        # 1. Mark as running
        await conn.execute(
            "UPDATE ingestion_jobs SET status='running', started_at=now() WHERE id=$1",
            job_id,
        )
        logger.debug(f"[JobQueue] job {job_id} marked running")

        # 2. Fetch data source config
        data_source = await conn.fetchrow(
            "SELECT source_type, config FROM data_sources WHERE id=$1 AND org_id=$2",
            data_source_id,
            org_id,
        )

        if not data_source:
            raise ValueError(f"Data source {data_source_id} not found")

        source_type_str = data_source["source_type"]
        config = data_source["config"]  # Already JSONB, will be dict

        logger.debug(f"[JobQueue] fetched source_type={source_type_str}")

        # 3. Build connector
        container = get_container()
        # Note: build_connector is not implemented in container.py yet
        # For now, we'll build the GoogleDriveConnector as an example
        # In production, implement build_connector(source_type_str, config, org_id)
        from adapters.connectors.google_drive import GoogleDriveConnector

        if source_type_str == "google_drive":
            connector = GoogleDriveConnector(
                credentials=config,
                org_id=org_id,
            )
        else:
            raise ValueError(f"Unknown source type: {source_type_str}")

        logger.debug(f"[JobQueue] built connector for {source_type_str}")

        # 4. Run ingestion
        ingestion_service = container["ingestion_service"]
        chunks_indexed = ingestion_service.ingest(
            connector=connector,
            org_id=org_id,
        )

        logger.info(f"[JobQueue] job {job_id} ingested {chunks_indexed} chunks")

        # 5. Mark as done
        await conn.execute(
            """
            UPDATE ingestion_jobs
            SET status='done', completed_at=now(), chunks_indexed=$2
            WHERE id=$1
            """,
            job_id,
            chunks_indexed,
        )

        logger.info(f"[JobQueue] job {job_id} completed successfully")

    except Exception as e:
        logger.error(f"[JobQueue] job {job_id} failed: {e}")

        # Mark as failed
        try:
            await conn.execute(
                """
                UPDATE ingestion_jobs
                SET status='failed', error_text=$2, completed_at=now()
                WHERE id=$1
                """,
                job_id,
                str(e)[:1000],  # Truncate error to 1000 chars
            )
        except Exception as update_err:
            logger.error(f"[JobQueue] failed to update job status: {update_err}")

    finally:
        await conn.close()


if __name__ == "__main__":
    # Run worker loop
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    asyncio.run(worker_loop())
