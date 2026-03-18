"""Bridge between the A1 agent and Celery workers for code execution."""

import logging
import uuid
from datetime import datetime, timezone

from celery.result import AsyncResult
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.job import Job
from ..tasks.execute import execute_bash, execute_python, execute_r

logger = logging.getLogger(__name__)

_TASK_MAP = {
    "python": execute_python,
    "r": execute_r,
    "bash": execute_bash,
}


def submit_job_sync(
    session_id: uuid.UUID,
    code: str,
    job_type: str,
    timeout: int | None = None,
) -> tuple[uuid.UUID, str]:
    """Submit a code execution job (called from sync context in monkey-patched functions).

    Creates a Job row via sync DB, dispatches a Celery task, returns (job_id, result).
    Blocks until the Celery task completes.
    """
    from ..tasks.db_sync import get_engine

    timeout = timeout or settings.celery_task_timeout
    job_id = uuid.uuid4()

    # Create job record
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            Job.__table__.insert().values(
                id=str(job_id),
                session_id=str(session_id),
                status="pending",
                job_type=job_type,
                code=code,
                created_at=datetime.now(timezone.utc),
            )
        )

    # Dispatch to Celery
    task_fn = _TASK_MAP.get(job_type)
    if not task_fn:
        raise ValueError(f"Unknown job type: {job_type}")

    async_result = task_fn.apply_async(
        args=[str(job_id), str(session_id), code, timeout],
        task_id=str(job_id),
        soft_time_limit=timeout,
        time_limit=timeout + 30,
    )

    # Update job with celery task ID
    with engine.begin() as conn:
        conn.execute(
            Job.__table__.update()
            .where(Job.__table__.c.id == str(job_id))
            .values(celery_task_id=async_result.id)
        )

    logger.info("Submitted %s job %s to Celery", job_type, job_id)

    # Block until result is ready
    try:
        result = async_result.get(timeout=timeout + 60)
    except Exception as e:
        logger.exception("Job %s failed or timed out", job_id)
        result = f"Error in execution: {e}"

    return job_id, result


async def list_jobs(
    db: AsyncSession, session_id: uuid.UUID, limit: int = 20, offset: int = 0
) -> list[Job]:
    result = await db.execute(
        select(Job)
        .where(Job.session_id == session_id)
        .order_by(Job.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> Job | None:
    result = await db.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def cancel_job(db: AsyncSession, job_id: uuid.UUID) -> Job | None:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job or job.status in ("completed", "failed", "cancelled"):
        return job

    # Revoke the Celery task
    if job.celery_task_id:
        from ..celery_app import celery

        celery.control.revoke(job.celery_task_id, terminate=True, signal="SIGTERM")

    job.status = "cancelled"
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(job)
    return job
