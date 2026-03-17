from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    agent_ready: bool
    database: str
    version: str
