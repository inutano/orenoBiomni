"""Authentication middleware — FastAPI dependency for resolving the current user.

When ``settings.auth_enabled`` is False (default), returns the anonymous user
so the app remains fully backward-compatible.
"""

import uuid
import logging

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models import User
from ..services import session_service
from ..services.auth_service import verify_jwt

logger = logging.getLogger(__name__)


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Resolve the current authenticated user.

    - auth_enabled=False  ->  anonymous user (backward compatible)
    - auth_enabled=True   ->  extract JWT from cookie or Authorization header,
                              look up user, or raise 401
    """
    if not settings.auth_enabled:
        return await session_service.get_or_create_default_user(db)

    # Try cookie first, then Authorization header
    token: str | None = request.cookies.get("auth_token")

    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_jwt(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Look up user in database
    try:
        user_id = uuid.UUID(payload["user_id"])
    except (ValueError, KeyError):
        raise HTTPException(status_code=401, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id, User.is_active.is_(True)))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user
