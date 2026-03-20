"""Schemas for file management endpoints."""

from datetime import datetime

from pydantic import BaseModel


class FileInfo(BaseModel):
    """Metadata about a single file in a session workspace."""

    name: str
    size: int
    content_type: str
    relative_path: str
    modified_at: datetime
    is_artifact: bool

    model_config = {"from_attributes": True}


class FileListResponse(BaseModel):
    """Response for listing files in a session workspace."""

    files: list[FileInfo]
    total_size: int


class FileUploadResponse(BaseModel):
    """Response after uploading files."""

    uploaded: list[FileInfo]
