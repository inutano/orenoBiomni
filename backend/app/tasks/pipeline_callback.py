"""Celery task to advance a pipeline after a step completes."""

import asyncio
import logging
import uuid

from ..celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name="backend.app.tasks.pipeline_callback.pipeline_step_done", bind=True)
def pipeline_step_done(self, pipeline_id: str, job_id: str):
    """Called after a pipeline step completes (success or error).

    Uses async DB via a fresh event loop since this runs in the Celery worker.
    """
    logger.info("Pipeline step done: pipeline=%s job=%s", pipeline_id, job_id)

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(_advance_pipeline(pipeline_id, job_id))
        finally:
            loop.close()
    except Exception:
        logger.exception(
            "Failed to advance pipeline %s after step %s", pipeline_id, job_id
        )


async def _advance_pipeline(pipeline_id: str, job_id: str) -> None:
    """Advance the pipeline using the async service."""
    from ..database import async_session
    from ..services import pipeline_service

    async with async_session() as db:
        await pipeline_service.on_step_complete(
            db, uuid.UUID(pipeline_id), job_id
        )
