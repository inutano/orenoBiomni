import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..schemas.job import JobListItem, JobRead
from ..services import execution_service

router = APIRouter(prefix="/jobs")


@router.get("/sessions/{session_id}", response_model=list[JobListItem])
async def list_jobs(
    session_id: uuid.UUID, limit: int = 20, offset: int = 0, db: AsyncSession = Depends(get_db)
):
    return await execution_service.list_jobs(db, session_id, limit, offset)


@router.get("/{job_id}", response_model=JobRead)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await execution_service.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/{job_id}/cancel", response_model=JobRead)
async def cancel_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await execution_service.cancel_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
