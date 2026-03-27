"""Celery tasks for sandboxed code execution."""

import glob
import logging
import os
import uuid
from datetime import datetime, timezone

import redis

from ..celery_app import celery
from ..config import settings
from .db_sync import update_job_status

logger = logging.getLogger(__name__)

_redis_client = None

# WES State constants (avoid importing models in worker)
RUNNING = "RUNNING"
COMPLETE = "COMPLETE"
EXECUTOR_ERROR = "EXECUTOR_ERROR"
SYSTEM_ERROR = "SYSTEM_ERROR"


def _get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url)
    return _redis_client


def _publish_status(job_id: str, state: str, detail: str = ""):
    """Publish job status to Redis pub/sub for SSE streaming."""
    import json

    _get_redis().publish(
        f"job:{job_id}:status",
        json.dumps({"state": state, "detail": detail}),
    )


def _ensure_workspace(session_id: str) -> str:
    workspace = os.path.join(settings.workspace_base_path, session_id)
    os.makedirs(workspace, exist_ok=True)
    return workspace


def _scan_new_files(workspace: str, since: float) -> list[dict]:
    """Scan workspace for files created after `since` timestamp."""
    artifacts = []
    for path in glob.glob(os.path.join(workspace, "**"), recursive=True):
        if os.path.isfile(path) and os.path.getmtime(path) > since:
            rel = os.path.relpath(path, workspace)
            artifacts.append(
                {
                    "filename": rel,
                    "size": os.path.getsize(path),
                    "path": path,
                }
            )
    return artifacts


def _notify_pipeline(pipeline_id: str | None, job_id: str) -> None:
    """If this job belongs to a pipeline, dispatch the callback to advance it."""
    if not pipeline_id:
        return
    try:
        from .pipeline_callback import pipeline_step_done
        pipeline_step_done.delay(pipeline_id, job_id)
    except Exception:
        logger.exception("Failed to dispatch pipeline callback for pipeline=%s job=%s", pipeline_id, job_id)


def _run_direct(code: str, workspace: str, job_type: str) -> str:
    """Run code directly in the worker process (legacy mode)."""
    old_cwd = os.getcwd()
    os.chdir(workspace)
    try:
        if job_type == "python":
            from biomni.tool.support_tools import run_python_repl
            return run_python_repl(code)
        elif job_type == "r":
            from biomni.utils import run_r_code
            return run_r_code(code)
        elif job_type == "bash":
            from biomni.utils import run_bash_script
            return run_bash_script(code)
        else:
            raise ValueError(f"Unknown job type: {job_type}")
    finally:
        os.chdir(old_cwd)


def _execute_job(task, job_id: str, session_id: str, code: str, timeout: int, job_type: str, pipeline_id: str | None = None):
    """Common execution logic shared by all code execution tasks.

    Decides whether to use sandbox (Docker container) or direct execution
    based on settings.sandbox_enabled.
    """
    jid = uuid.UUID(job_id)
    now = datetime.now(timezone.utc)
    update_job_status(jid, RUNNING, worker_id=task.request.hostname, started_at=now)
    _publish_status(job_id, RUNNING)

    workspace = _ensure_workspace(session_id)
    scan_start = now.timestamp()

    try:
        if settings.sandbox_enabled:
            from .sandbox import run_in_sandbox

            stdout, stderr, exit_code = run_in_sandbox(
                job_id, session_id, code, job_type, timeout,
            )
            result = stdout
            if exit_code != 0:
                raise RuntimeError(stderr or f"Sandbox exited with code {exit_code}")
        else:
            result = _run_direct(code, workspace, job_type)

        artifacts = _scan_new_files(workspace, scan_start)
        update_job_status(
            jid,
            COMPLETE,
            stdout=result,
            exit_code=0,
            artifacts={"files": artifacts} if artifacts else None,
            completed_at=datetime.now(timezone.utc),
        )
        _publish_status(job_id, COMPLETE)
        _notify_pipeline(pipeline_id, job_id)
        return result

    except Exception as e:
        logger.exception("%s execution failed for job %s", job_type.capitalize(), job_id)
        update_job_status(
            jid, EXECUTOR_ERROR,
            stderr=str(e), exit_code=1,
            completed_at=datetime.now(timezone.utc),
        )
        _publish_status(job_id, EXECUTOR_ERROR, str(e))
        _notify_pipeline(pipeline_id, job_id)
        return f"Error in execution: {e}"


@celery.task(name="backend.app.tasks.execute.execute_python", bind=True)
def execute_python(self, job_id: str, session_id: str, code: str, timeout: int, pipeline_id: str | None = None):
    return _execute_job(self, job_id, session_id, code, timeout, "python", pipeline_id)


@celery.task(name="backend.app.tasks.execute.execute_r", bind=True)
def execute_r(self, job_id: str, session_id: str, code: str, timeout: int, pipeline_id: str | None = None):
    return _execute_job(self, job_id, session_id, code, timeout, "r", pipeline_id)


@celery.task(name="backend.app.tasks.execute.execute_bash", bind=True)
def execute_bash(self, job_id: str, session_id: str, code: str, timeout: int, pipeline_id: str | None = None):
    return _execute_job(self, job_id, session_id, code, timeout, "bash", pipeline_id)
