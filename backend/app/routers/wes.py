"""GA4GH WES v1.1.0 compatible API router.

Mounted at /ga4gh/wes/v1/
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models.job import Job, RunState
from ..schemas.wes import (
    DefaultWorkflowEngineParameter,
    ErrorResponse,
    Log,
    RunId,
    RunListResponse,
    RunLog,
    RunRequest,
    RunStatus,
    RunSubmitRequest,
    RunSummary,
    ServiceInfo,
    State,
    TaskListResponse,
    TaskLog,
    WorkflowTypeVersion,
)
from ..services import execution_service

router = APIRouter()


def _job_to_run_log(job: Job, request_url: str = "") -> RunLog:
    """Convert internal Job model to WES RunLog."""
    return RunLog(
        run_id=str(job.id),
        request=RunRequest(
            workflow_type=job.job_type,
            workflow_params={"code": job.code},
            tags=job.tags or {},
        ),
        state=State(job.state),
        run_log=Log(
            name=f"{job.job_type} execution",
            cmd=[job.code] if job.code else None,
            start_time=job.started_at.isoformat() if job.started_at else None,
            end_time=job.completed_at.isoformat() if job.completed_at else None,
            stdout=job.stdout,
            stderr=job.stderr,
            exit_code=job.exit_code,
            system_logs=[f"worker={job.worker_id}"] if job.worker_id else None,
        ),
        task_logs_url=f"{request_url}/{job.id}/tasks" if request_url else None,
        outputs=job.artifacts,
    )


def _job_to_run_summary(job: Job) -> RunSummary:
    return RunSummary(
        run_id=str(job.id),
        state=State(job.state),
        start_time=job.started_at.isoformat() if job.started_at else None,
        end_time=job.completed_at.isoformat() if job.completed_at else None,
        tags=job.tags or {},
    )


def _job_to_task_log(job: Job) -> TaskLog:
    """For single-step runs, the run itself is the only task."""
    return TaskLog(
        id=str(job.id),
        name=f"{job.job_type} execution",
        cmd=[job.code] if job.code else None,
        start_time=job.started_at.isoformat() if job.started_at else None,
        end_time=job.completed_at.isoformat() if job.completed_at else None,
        stdout=job.stdout,
        stderr=job.stderr,
        exit_code=job.exit_code,
        system_logs=[f"worker={job.worker_id}"] if job.worker_id else None,
    )


# --- Endpoints ---


@router.get("/service-info", response_model=ServiceInfo)
async def service_info(db: AsyncSession = Depends(get_db)):
    # Count runs per state
    result = await db.execute(
        select(Job.state, func.count()).group_by(Job.state)
    )
    state_counts = {row[0]: row[1] for row in result.all()}

    return ServiceInfo(
        workflow_type_versions={
            "python": WorkflowTypeVersion(workflow_type_version=["3.11"]),
            "r": WorkflowTypeVersion(workflow_type_version=["4.x"]),
            "bash": WorkflowTypeVersion(workflow_type_version=["5.x"]),
        },
        supported_wes_versions=["1.1.0"],
        supported_filesystem_protocols=["file"],
        workflow_engine_versions={"celery": "5.4"},
        default_workflow_engine_parameters=[
            DefaultWorkflowEngineParameter(
                name="timeout",
                type="int",
                default_value=str(settings.celery_task_timeout),
            ),
        ],
        system_state_counts=state_counts,
        tags={
            "service": "orenoBiomni",
            "llm": settings.biomni_llm,
        },
    )


@router.get("/runs", response_model=RunListResponse)
async def list_runs(
    page_size: int = Query(default=20, ge=1, le=100),
    page_token: str | None = None,
    session_id: str | None = Query(default=None, description="Filter by session"),
    db: AsyncSession = Depends(get_db),
):
    query = select(Job).order_by(Job.created_at.desc())

    if session_id:
        query = query.where(Job.session_id == uuid.UUID(session_id))

    # Token-based pagination: page_token is the last run_id seen
    if page_token:
        # Get the created_at of the token job to paginate
        token_result = await db.execute(
            select(Job.created_at).where(Job.id == uuid.UUID(page_token))
        )
        token_time = token_result.scalar_one_or_none()
        if token_time:
            query = query.where(Job.created_at < token_time)

    query = query.limit(page_size + 1)  # fetch one extra to detect next page

    result = await db.execute(query)
    jobs = list(result.scalars().all())

    has_next = len(jobs) > page_size
    if has_next:
        jobs = jobs[:page_size]

    runs = [_job_to_run_summary(j) for j in jobs]
    next_token = str(jobs[-1].id) if has_next and jobs else None

    return RunListResponse(runs=runs, next_page_token=next_token)


@router.post("/runs", response_model=RunId, status_code=200)
async def submit_run(body: RunSubmitRequest, db: AsyncSession = Depends(get_db)):
    code = body.workflow_params.get("code")
    session_id_str = body.workflow_params.get("session_id")

    if not code:
        raise HTTPException(status_code=400, detail="workflow_params.code is required")
    if not session_id_str:
        raise HTTPException(status_code=400, detail="workflow_params.session_id is required")

    try:
        sid = uuid.UUID(session_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id")

    job = Job(
        session_id=sid,
        state=RunState.QUEUED,
        job_type=body.workflow_type,
        code=code,
        tags=body.tags or None,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Dispatch to Celery
    await execution_service.dispatch_job_async(job)

    return RunId(run_id=str(job.id))


@router.get("/runs/{run_id}", response_model=RunLog)
async def get_run(run_id: str, db: AsyncSession = Depends(get_db)):
    job = await execution_service.get_job(db, uuid.UUID(run_id))
    if not job:
        raise HTTPException(status_code=404, detail="Run not found")
    return _job_to_run_log(job)


@router.get("/runs/{run_id}/status", response_model=RunStatus)
async def get_run_status(run_id: str, db: AsyncSession = Depends(get_db)):
    job = await execution_service.get_job(db, uuid.UUID(run_id))
    if not job:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunStatus(run_id=str(job.id), state=State(job.state))


@router.get("/runs/{run_id}/tasks", response_model=TaskListResponse)
async def list_run_tasks(run_id: str, db: AsyncSession = Depends(get_db)):
    job = await execution_service.get_job(db, uuid.UUID(run_id))
    if not job:
        raise HTTPException(status_code=404, detail="Run not found")
    # Single-step: the run itself is the only task
    return TaskListResponse(task_logs=[_job_to_task_log(job)])


@router.get("/runs/{run_id}/tasks/{task_id}", response_model=TaskLog)
async def get_run_task(run_id: str, task_id: str, db: AsyncSession = Depends(get_db)):
    job = await execution_service.get_job(db, uuid.UUID(run_id))
    if not job:
        raise HTTPException(status_code=404, detail="Run not found")
    if str(job.id) != task_id:
        raise HTTPException(status_code=404, detail="Task not found")
    return _job_to_task_log(job)


@router.post("/runs/{run_id}/cancel", response_model=RunId)
async def cancel_run(run_id: str, db: AsyncSession = Depends(get_db)):
    job = await execution_service.cancel_job(db, uuid.UUID(run_id))
    if not job:
        raise HTTPException(status_code=404, detail="Run not found")
    return RunId(run_id=str(job.id))
