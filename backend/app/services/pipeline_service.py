"""Pipeline orchestration service — create, advance, cancel multi-step pipelines."""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.job import Job, RunState
from ..models.pipeline import Pipeline
from ..schemas.pipeline import PipelineStep, StepResult
from ..tasks.execute import execute_bash, execute_python, execute_r

logger = logging.getLogger(__name__)
audit = logging.getLogger("audit")

_TASK_MAP = {
    "python": execute_python,
    "r": execute_r,
    "bash": execute_bash,
}


async def create_pipeline(
    db: AsyncSession,
    session_id: uuid.UUID,
    name: str,
    description: str | None,
    steps: list[PipelineStep],
) -> Pipeline:
    """Create a Pipeline row and a Job row for each step, then start root steps."""
    pipeline = Pipeline(
        session_id=session_id,
        name=name,
        description=description,
        state=RunState.QUEUED,
        total_steps=len(steps),
        current_step=0,
    )
    db.add(pipeline)
    await db.flush()  # get pipeline.id

    # Build JSONB steps list, creating a Job for each step
    steps_data = []
    for idx, step in enumerate(steps):
        job = Job(
            session_id=session_id,
            state=RunState.QUEUED,
            job_type=step.job_type,
            code=step.code,
            tags={"pipeline_id": str(pipeline.id), "step_index": str(idx)},
        )
        db.add(job)
        await db.flush()

        steps_data.append({
            "index": idx,
            "name": step.name,
            "job_type": step.job_type,
            "code": step.code,
            "depends_on": step.depends_on,
            "job_id": str(job.id),
            "state": RunState.QUEUED,
        })

    pipeline.steps = steps_data
    await db.commit()
    await db.refresh(pipeline)

    # Start root steps (no dependencies)
    await start_next_steps(db, pipeline)
    return pipeline


async def start_next_steps(db: AsyncSession, pipeline: Pipeline) -> None:
    """Find steps whose dependencies are all COMPLETE and dispatch them."""
    steps = pipeline.steps
    dispatched = False

    for step in steps:
        if step["state"] != RunState.QUEUED:
            continue

        # Check all dependencies are COMPLETE
        deps_met = all(
            steps[dep_idx]["state"] == RunState.COMPLETE
            for dep_idx in step.get("depends_on", [])
        )
        if not deps_met:
            continue

        # Dispatch this step
        job_id = step["job_id"]
        task_fn = _TASK_MAP.get(step["job_type"])
        if not task_fn:
            logger.error("Unknown job type %s for step %s", step["job_type"], step["name"])
            continue

        timeout = settings.celery_task_timeout

        task_fn.apply_async(
            args=[job_id, str(pipeline.session_id), step["code"], timeout],
            kwargs={"pipeline_id": str(pipeline.id)},
            task_id=job_id,
            soft_time_limit=timeout,
            time_limit=timeout + 30,
        )

        # Update step and job state
        step["state"] = RunState.RUNNING
        dispatched = True

        audit.info(
            "PIPELINE_STEP_START pipeline=%s step=%s job=%s type=%s",
            pipeline.id, step["name"], job_id, step["job_type"],
        )

    if dispatched:
        if pipeline.state == RunState.QUEUED:
            pipeline.state = RunState.RUNNING
            pipeline.started_at = datetime.now(timezone.utc)

        # Update current_step to the highest running/complete index
        pipeline.current_step = max(
            (s["index"] for s in steps if s["state"] in (RunState.RUNNING, RunState.COMPLETE)),
            default=0,
        )

        # Force JSONB update
        pipeline.steps = list(steps)
        await db.commit()
        await db.refresh(pipeline)


async def on_step_complete(db: AsyncSession, pipeline_id: uuid.UUID, job_id: str) -> None:
    """Called when a step's job finishes. Refresh state from DB and advance."""
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        logger.error("Pipeline %s not found for step completion", pipeline_id)
        return

    if pipeline.state in (RunState.CANCELED, RunState.COMPLETE, RunState.EXECUTOR_ERROR):
        return

    # Refresh the job state from the jobs table
    job_result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
    job = job_result.scalar_one_or_none()
    if not job:
        logger.error("Job %s not found for pipeline %s", job_id, pipeline_id)
        return

    # Update the step's state in the JSONB
    steps = list(pipeline.steps)
    for step in steps:
        if step["job_id"] == job_id:
            step["state"] = job.state
            break

    pipeline.steps = steps

    # Check if any step errored
    errored = any(s["state"] in (RunState.EXECUTOR_ERROR, RunState.SYSTEM_ERROR) for s in steps)
    if errored:
        pipeline.state = RunState.EXECUTOR_ERROR
        pipeline.completed_at = datetime.now(timezone.utc)
        pipeline.current_step = max(
            (s["index"] for s in steps if s["state"] != RunState.QUEUED),
            default=0,
        )
        await db.commit()
        audit.info("PIPELINE_ERROR pipeline=%s failed_job=%s", pipeline_id, job_id)
        return

    # Check if all steps are complete
    all_complete = all(s["state"] == RunState.COMPLETE for s in steps)
    if all_complete:
        pipeline.state = RunState.COMPLETE
        pipeline.completed_at = datetime.now(timezone.utc)
        pipeline.current_step = pipeline.total_steps
        await db.commit()
        audit.info("PIPELINE_COMPLETE pipeline=%s", pipeline_id)
        return

    # Otherwise, advance — dispatch next ready steps
    pipeline.current_step = max(
        (s["index"] for s in steps if s["state"] in (RunState.RUNNING, RunState.COMPLETE)),
        default=0,
    )
    await db.commit()
    await db.refresh(pipeline)
    await start_next_steps(db, pipeline)


async def cancel_pipeline(db: AsyncSession, pipeline_id: uuid.UUID) -> Pipeline | None:
    """Cancel a pipeline and all its pending/running jobs."""
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        return None

    if pipeline.state in (RunState.COMPLETE, RunState.CANCELED):
        return pipeline

    from ..celery_app import celery as celery_app

    steps = list(pipeline.steps)
    for step in steps:
        if step["state"] in (RunState.QUEUED, RunState.RUNNING):
            # Revoke celery task
            celery_app.control.revoke(step["job_id"], terminate=True, signal="SIGTERM")
            step["state"] = RunState.CANCELED

            # Update the job row too
            job_result = await db.execute(select(Job).where(Job.id == uuid.UUID(step["job_id"])))
            job = job_result.scalar_one_or_none()
            if job:
                job.state = RunState.CANCELED
                job.completed_at = datetime.now(timezone.utc)

    pipeline.steps = steps
    pipeline.state = RunState.CANCELED
    pipeline.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(pipeline)

    audit.info("PIPELINE_CANCELED pipeline=%s", pipeline_id)
    return pipeline


async def get_pipeline(db: AsyncSession, pipeline_id: uuid.UUID) -> Pipeline | None:
    """Get pipeline and enrich steps with latest job data."""
    result = await db.execute(select(Pipeline).where(Pipeline.id == pipeline_id))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        return None

    # Enrich steps with job data
    steps = list(pipeline.steps)
    job_ids = [uuid.UUID(s["job_id"]) for s in steps if s.get("job_id")]
    if job_ids:
        jobs_result = await db.execute(select(Job).where(Job.id.in_(job_ids)))
        jobs_by_id = {str(j.id): j for j in jobs_result.scalars().all()}

        for step in steps:
            job = jobs_by_id.get(step.get("job_id"))
            if job:
                step["state"] = job.state
                step["stdout"] = job.stdout
                step["stderr"] = job.stderr
                step["exit_code"] = job.exit_code
                step["started_at"] = job.started_at.isoformat() if job.started_at else None
                step["completed_at"] = job.completed_at.isoformat() if job.completed_at else None

    pipeline.steps = steps
    return pipeline


async def list_pipelines(
    db: AsyncSession, session_id: uuid.UUID | None = None, limit: int = 50
) -> list[Pipeline]:
    """List pipelines, optionally filtered by session."""
    query = select(Pipeline).order_by(Pipeline.created_at.desc()).limit(limit)
    if session_id:
        query = query.where(Pipeline.session_id == session_id)
    result = await db.execute(query)
    return list(result.scalars().all())


def get_step_results(pipeline: Pipeline) -> list[StepResult]:
    """Convert pipeline steps JSONB to StepResult schemas."""
    results = []
    for step in pipeline.steps:
        results.append(StepResult(
            index=step["index"],
            name=step["name"],
            job_type=step["job_type"],
            code=step["code"],
            depends_on=step.get("depends_on", []),
            job_id=step.get("job_id"),
            state=step.get("state", "QUEUED"),
            stdout=step.get("stdout"),
            stderr=step.get("stderr"),
            exit_code=step.get("exit_code"),
            started_at=step.get("started_at"),
            completed_at=step.get("completed_at"),
        ))
    return results
