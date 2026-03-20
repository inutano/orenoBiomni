"""Pipeline schemas for multi-step execution."""

from datetime import datetime

from pydantic import BaseModel, Field


class PipelineStep(BaseModel):
    """A single step definition within a pipeline."""

    name: str
    job_type: str  # python, r, bash
    code: str
    depends_on: list[int] = Field(default_factory=list)


class PipelineCreate(BaseModel):
    """Request body for creating a pipeline."""

    name: str
    description: str | None = None
    session_id: str
    steps: list[PipelineStep]


class StepResult(BaseModel):
    """A step with its job execution result embedded."""

    index: int
    name: str
    job_type: str
    code: str
    depends_on: list[int]
    job_id: str | None = None
    state: str = "QUEUED"
    stdout: str | None = None
    stderr: str | None = None
    exit_code: int | None = None
    started_at: str | None = None
    completed_at: str | None = None


class PipelineRead(BaseModel):
    """Full pipeline detail response."""

    id: str
    name: str
    description: str | None = None
    state: str
    steps: list[StepResult]
    current_step: int
    total_steps: int
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None


class PipelineListItem(BaseModel):
    """Summary for pipeline list views."""

    id: str
    name: str
    state: str
    current_step: int
    total_steps: int
    created_at: str


class PipelineTemplate(BaseModel):
    """A predefined pipeline template."""

    name: str
    description: str
    steps: list[PipelineStep]
