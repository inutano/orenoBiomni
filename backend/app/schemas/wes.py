"""GA4GH Workflow Execution Service (WES) v1.1.0 compatible schemas."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class State(StrEnum):
    UNKNOWN = "UNKNOWN"
    QUEUED = "QUEUED"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETE = "COMPLETE"
    EXECUTOR_ERROR = "EXECUTOR_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    CANCELED = "CANCELED"
    CANCELING = "CANCELING"
    PREEMPTED = "PREEMPTED"


# --- Responses ---


class RunId(BaseModel):
    run_id: str


class RunStatus(BaseModel):
    run_id: str
    state: State


class Log(BaseModel):
    name: str | None = None
    cmd: list[str] | None = None
    start_time: str | None = None
    end_time: str | None = None
    stdout: str | None = None
    stderr: str | None = None
    exit_code: int | None = None
    system_logs: list[str] | None = None


class TaskLog(Log):
    id: str
    tes_uri: str | None = None


class RunRequest(BaseModel):
    workflow_params: dict | None = None
    workflow_type: str | None = None
    workflow_type_version: str | None = None
    workflow_url: str | None = None
    tags: dict[str, str] | None = None
    workflow_engine: str | None = None
    workflow_engine_version: str | None = None
    workflow_engine_parameters: dict[str, str] | None = None


class RunLog(BaseModel):
    run_id: str
    request: RunRequest | None = None
    state: State
    run_log: Log | None = None
    task_logs_url: str | None = None
    outputs: dict | None = None


class RunSummary(BaseModel):
    run_id: str
    state: State
    start_time: str | None = None
    end_time: str | None = None
    tags: dict[str, str] = Field(default_factory=dict)


class RunListResponse(BaseModel):
    runs: list[RunSummary]
    next_page_token: str | None = None


class TaskListResponse(BaseModel):
    task_logs: list[TaskLog]
    next_page_token: str | None = None


class WorkflowTypeVersion(BaseModel):
    workflow_type_version: list[str] = Field(default_factory=list)


class DefaultWorkflowEngineParameter(BaseModel):
    name: str | None = None
    type: str | None = None
    default_value: str | None = None


class ServiceInfo(BaseModel):
    workflow_type_versions: dict[str, WorkflowTypeVersion]
    supported_wes_versions: list[str]
    supported_filesystem_protocols: list[str]
    workflow_engine_versions: dict[str, str]
    default_workflow_engine_parameters: list[DefaultWorkflowEngineParameter]
    system_state_counts: dict[str, int]
    tags: dict[str, str] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    msg: str
    status_code: int


# --- Request bodies ---


class RunSubmitRequest(BaseModel):
    """Simplified run submission for orenoBiomni (code execution)."""

    workflow_type: str = "python"  # python, r, bash
    workflow_params: dict = Field(default_factory=dict)  # {"code": "...", "session_id": "..."}
    tags: dict[str, str] = Field(default_factory=dict)
