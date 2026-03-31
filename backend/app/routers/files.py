"""File management API router.

To register in main.py, add:
    from .routers import files
    app.include_router(files.router, prefix="/api/v1", tags=["files"])
"""

import logging
import mimetypes
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..schemas.files import FileInfo, FileListResponse, FileUploadResponse
from ..services import session_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions/{session_id}/files")

MAX_FILE_SIZE = settings.max_upload_size_mb * 1024 * 1024


def _workspace_path(session_id: uuid.UUID) -> Path:
    """Return the workspace root for a session."""
    return Path(settings.workspace_base_path) / str(session_id)


def _validate_path(workspace: Path, file_path: str) -> Path:
    """Resolve a relative file path and ensure it stays within the workspace.

    Raises HTTPException 400 on path traversal attempts.
    """
    resolved = (workspace / file_path).resolve()
    workspace_resolved = workspace.resolve()
    if not str(resolved).startswith(str(workspace_resolved) + "/") and resolved != workspace_resolved:
        raise HTTPException(status_code=400, detail="Invalid file path")
    return resolved


def _guess_content_type(path: Path) -> str:
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "application/octet-stream"


def _file_info(workspace: Path, file: Path) -> FileInfo:
    """Build FileInfo from a concrete file path."""
    stat = file.stat()
    rel = str(file.relative_to(workspace))
    # Files under job subdirectories (not uploads/) are considered artifacts
    is_artifact = not rel.startswith("uploads/")
    return FileInfo(
        name=file.name,
        size=stat.st_size,
        content_type=_guess_content_type(file),
        relative_path=rel,
        modified_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc),
        is_artifact=is_artifact,
    )


async def _require_active_session(db: AsyncSession, session_id: uuid.UUID) -> None:
    """Validate that a session exists and is active, or raise 404."""
    session = await session_service.get_session(db, session_id)
    if not session or not session.is_active:
        raise HTTPException(status_code=404, detail="Session not found")


# --- Endpoints ---


@router.post("", response_model=FileUploadResponse, status_code=201)
async def upload_files(
    session_id: uuid.UUID,
    files: list[UploadFile],
    db: AsyncSession = Depends(get_db),
):
    """Upload one or more files to the session workspace uploads/ directory."""
    await _require_active_session(db, session_id)

    workspace = _workspace_path(session_id)
    upload_dir = workspace / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    uploaded: list[FileInfo] = []
    for f in files:
        if not f.filename:
            continue

        # Sanitize filename — use only the basename
        safe_name = Path(f.filename).name
        if not safe_name:
            continue

        dest = upload_dir / safe_name
        _validate_path(workspace, f"uploads/{safe_name}")

        # Read and check size
        content = await f.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File '{safe_name}' exceeds {MAX_FILE_SIZE // (1024 * 1024)} MB limit",
            )

        dest.write_bytes(content)
        uploaded.append(_file_info(workspace, dest))
        logger.info("Uploaded file %s for session %s (%d bytes)", safe_name, session_id, len(content))

    return FileUploadResponse(uploaded=uploaded)


@router.get("", response_model=FileListResponse)
async def list_files(
    session_id: uuid.UUID,
    limit: int = Query(default=200, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """List files in the session workspace (uploads and job artifacts)."""
    await _require_active_session(db, session_id)

    workspace = _workspace_path(session_id)
    if not workspace.exists():
        return FileListResponse(files=[], total_size=0)

    file_list: list[FileInfo] = []
    total_size = 0

    for file in sorted(workspace.rglob("*")):
        if not file.is_file():
            continue
        info = _file_info(workspace, file)
        total_size += info.size
        if len(file_list) < limit:
            file_list.append(info)

    return FileListResponse(files=file_list, total_size=total_size)


@router.get("/{file_path:path}")
async def get_file(
    session_id: uuid.UUID,
    file_path: str,
    preview: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
):
    """Download or preview a file from the session workspace."""
    await _require_active_session(db, session_id)

    workspace = _workspace_path(session_id)
    resolved = _validate_path(workspace, file_path)

    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    content_type = _guess_content_type(resolved)

    if preview:
        # For text files and images, return content inline
        if content_type.startswith("text/") or content_type in (
            "application/json",
            "application/xml",
        ):
            text = resolved.read_text(errors="replace")
            return Response(content=text, media_type=content_type)
        if content_type.startswith("image/"):
            return FileResponse(
                path=str(resolved),
                media_type=content_type,
                headers={"Content-Disposition": "inline"},
            )

    return FileResponse(
        path=str(resolved),
        media_type=content_type,
        filename=resolved.name,
    )


@router.delete("/{file_path:path}", status_code=204)
async def delete_file(
    session_id: uuid.UUID,
    file_path: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a file from the session workspace."""
    await _require_active_session(db, session_id)

    workspace = _workspace_path(session_id)
    resolved = _validate_path(workspace, file_path)

    if not resolved.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    resolved.unlink()
    logger.info("Deleted file %s for session %s", file_path, session_id)

    # Clean up empty parent directories up to workspace root
    parent = resolved.parent
    workspace_resolved = workspace.resolve()
    while parent != workspace_resolved and parent.is_dir() and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent
