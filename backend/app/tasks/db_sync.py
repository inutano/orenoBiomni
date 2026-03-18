"""Synchronous DB helpers for Celery workers (cannot use asyncpg)."""

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, text

from ..config import settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(settings.database_url_sync, echo=False)
    return _engine


def update_job_status(
    job_id: uuid.UUID,
    state: str,
    *,
    stdout: str | None = None,
    stderr: str | None = None,
    exit_code: int | None = None,
    artifacts: dict | None = None,
    worker_id: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> None:
    engine = get_engine()
    values: dict = {"state": state}
    if stdout is not None:
        values["stdout"] = stdout
    if stderr is not None:
        values["stderr"] = stderr
    if exit_code is not None:
        values["exit_code"] = exit_code
    if artifacts is not None:
        # JSONB needs to be serialized for raw SQL
        values["artifacts"] = json.dumps(artifacts)
    if worker_id is not None:
        values["worker_id"] = worker_id
    if started_at is not None:
        values["started_at"] = started_at
    if completed_at is not None:
        values["completed_at"] = completed_at

    # Build SET clause with proper casting for JSONB
    set_parts = []
    for k in values:
        if k == "artifacts":
            set_parts.append(f"{k} = CAST(:{k} AS jsonb)")
        else:
            set_parts.append(f"{k} = :{k}")

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE jobs SET " + ", ".join(set_parts) + " WHERE id = :job_id"),
            {**values, "job_id": str(job_id)},
        )
