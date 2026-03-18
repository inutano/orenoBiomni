from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    agent_ready: bool
    database: str
    redis: str = "not_configured"
    celery_active: bool = False
    version: str
