import uuid
from datetime import datetime

from pydantic import BaseModel


class JobRead(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    message_id: uuid.UUID | None = None
    status: str
    job_type: str
    code: str
    result: str | None = None
    artifacts: dict | None = None
    error: str | None = None
    celery_task_id: str | None = None
    worker_id: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class JobListItem(BaseModel):
    id: uuid.UUID
    status: str
    job_type: str
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}
