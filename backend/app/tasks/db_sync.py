"""Synchronous DB helpers for Celery workers (cannot use asyncpg)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine, text, update
from sqlalchemy.orm import Session

from ..config import settings

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(settings.database_url_sync, echo=False)
    return _engine


def update_job_status(
    job_id: uuid.UUID,
    status: str,
    *,
    result: str | None = None,
    error: str | None = None,
    artifacts: dict | None = None,
    worker_id: str | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> None:
    engine = get_engine()
    values: dict = {"status": status}
    if result is not None:
        values["result"] = result
    if error is not None:
        values["error"] = error
    if artifacts is not None:
        values["artifacts"] = artifacts
    if worker_id is not None:
        values["worker_id"] = worker_id
    if started_at is not None:
        values["started_at"] = started_at
    if completed_at is not None:
        values["completed_at"] = completed_at

    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE jobs SET "
                + ", ".join(f"{k} = :{k}" for k in values)
                + " WHERE id = :job_id"
            ),
            {**values, "job_id": str(job_id)},
        )
