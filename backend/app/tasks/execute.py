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


@celery.task(name="backend.app.tasks.execute.execute_python", bind=True)
def execute_python(self, job_id: str, session_id: str, code: str, timeout: int):
    jid = uuid.UUID(job_id)
    now = datetime.now(timezone.utc)
    update_job_status(jid, RUNNING, worker_id=self.request.hostname, started_at=now)
    _publish_status(job_id, RUNNING)

    workspace = _ensure_workspace(session_id)
    scan_start = now.timestamp()

    try:
        from biomni.tool.support_tools import run_python_repl

        old_cwd = os.getcwd()
        os.chdir(workspace)
        try:
            result = run_python_repl(code)
        finally:
            os.chdir(old_cwd)

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
        return result

    except Exception as e:
        logger.exception("Python execution failed for job %s", job_id)
        update_job_status(
            jid, EXECUTOR_ERROR,
            stderr=str(e), exit_code=1,
            completed_at=datetime.now(timezone.utc),
        )
        _publish_status(job_id, EXECUTOR_ERROR, str(e))
        return f"Error in execution: {e}"


@celery.task(name="backend.app.tasks.execute.execute_r", bind=True)
def execute_r(self, job_id: str, session_id: str, code: str, timeout: int):
    jid = uuid.UUID(job_id)
    now = datetime.now(timezone.utc)
    update_job_status(jid, RUNNING, worker_id=self.request.hostname, started_at=now)
    _publish_status(job_id, RUNNING)

    workspace = _ensure_workspace(session_id)
    scan_start = now.timestamp()

    try:
        from biomni.utils import run_r_code

        old_cwd = os.getcwd()
        os.chdir(workspace)
        try:
            result = run_r_code(code)
        finally:
            os.chdir(old_cwd)

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
        return result

    except Exception as e:
        logger.exception("R execution failed for job %s", job_id)
        update_job_status(
            jid, EXECUTOR_ERROR,
            stderr=str(e), exit_code=1,
            completed_at=datetime.now(timezone.utc),
        )
        _publish_status(job_id, EXECUTOR_ERROR, str(e))
        return f"Error in execution: {e}"


@celery.task(name="backend.app.tasks.execute.execute_bash", bind=True)
def execute_bash(self, job_id: str, session_id: str, code: str, timeout: int):
    jid = uuid.UUID(job_id)
    now = datetime.now(timezone.utc)
    update_job_status(jid, RUNNING, worker_id=self.request.hostname, started_at=now)
    _publish_status(job_id, RUNNING)

    workspace = _ensure_workspace(session_id)
    scan_start = now.timestamp()

    try:
        from biomni.utils import run_bash_script

        old_cwd = os.getcwd()
        os.chdir(workspace)
        try:
            result = run_bash_script(code)
        finally:
            os.chdir(old_cwd)

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
        return result

    except Exception as e:
        logger.exception("Bash execution failed for job %s", job_id)
        update_job_status(
            jid, EXECUTOR_ERROR,
            stderr=str(e), exit_code=1,
            completed_at=datetime.now(timezone.utc),
        )
        _publish_status(job_id, EXECUTOR_ERROR, str(e))
        return f"Error in execution: {e}"
