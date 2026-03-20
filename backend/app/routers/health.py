from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..schemas.health import HealthResponse
from ..services import agent_manager

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(db: AsyncSession = Depends(get_db)):
    db_status = "connected"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    redis_status = "not_configured"
    if settings.redis_url:
        try:
            import redis

            r = redis.from_url(settings.redis_url, socket_connect_timeout=2)
            r.ping()
            r.close()
            redis_status = "connected"
        except Exception:
            redis_status = "error"

    celery_status = "inactive"
    if agent_manager.is_celery_active():
        try:
            from ..celery_app import celery

            inspect = celery.control.inspect(timeout=2)
            pong = inspect.ping()
            celery_status = "connected" if pong else "no_workers"
        except Exception:
            celery_status = "error"

    return HealthResponse(
        status="ok",
        agent_ready=agent_manager.is_agent_ready(),
        database=db_status,
        redis=redis_status,
        celery_active=agent_manager.is_celery_active(),
        celery_status=celery_status,
        version="0.1.0",
    )
