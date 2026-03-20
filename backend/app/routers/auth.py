"""OAuth authentication endpoints.

To register this router, add the following to main.py:

    from .routers import auth
    app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
"""

import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..middleware.auth import get_current_user
from ..models import User
from ..services.auth_service import (
    create_jwt,
    exchange_github_code,
    exchange_google_code,
    get_or_create_oauth_user,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")

# ---------------------------------------------------------------------------
# Provider discovery
# ---------------------------------------------------------------------------


@router.get("/providers")
async def get_providers():
    """Return which OAuth providers are configured and whether auth is enabled."""
    return {
        "auth_enabled": settings.auth_enabled,
        "google": bool(settings.google_client_id and settings.google_client_secret),
        "github": bool(settings.github_client_id and settings.github_client_secret),
    }


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------


@router.get("/login/google")
async def login_google():
    """Redirect to Google OAuth consent screen."""
    if not settings.google_client_id:
        raise HTTPException(status_code=404, detail="Google OAuth not configured")

    params = urlencode({
        "client_id": settings.google_client_id,
        "redirect_uri": f"{settings.auth_redirect_url}/api/v1/auth/callback/google",
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    })
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@router.get("/callback/google")
async def callback_google(code: str, db: AsyncSession = Depends(get_db)):
    """Handle Google OAuth callback: exchange code, create/find user, set cookie."""
    if not settings.google_client_id:
        raise HTTPException(status_code=404, detail="Google OAuth not configured")

    try:
        user_info = await exchange_google_code(code)
    except Exception:
        logger.exception("Google OAuth code exchange failed")
        raise HTTPException(status_code=400, detail="Failed to authenticate with Google")

    user = await get_or_create_oauth_user(
        db,
        provider="google",
        provider_id=user_info["provider_id"],
        email=user_info["email"],
        display_name=user_info.get("name"),
        avatar_url=user_info.get("picture"),
    )

    token = create_jwt(str(user.id), user.email)
    response = RedirectResponse(settings.auth_redirect_url, status_code=302)
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,  # 7 days
        path="/",
    )
    return response


# ---------------------------------------------------------------------------
# GitHub OAuth
# ---------------------------------------------------------------------------


@router.get("/login/github")
async def login_github():
    """Redirect to GitHub OAuth authorization screen."""
    if not settings.github_client_id:
        raise HTTPException(status_code=404, detail="GitHub OAuth not configured")

    params = urlencode({
        "client_id": settings.github_client_id,
        "redirect_uri": f"{settings.auth_redirect_url}/api/v1/auth/callback/github",
        "scope": "read:user user:email",
    })
    return RedirectResponse(f"https://github.com/login/oauth/authorize?{params}")


@router.get("/callback/github")
async def callback_github(code: str, db: AsyncSession = Depends(get_db)):
    """Handle GitHub OAuth callback: exchange code, create/find user, set cookie."""
    if not settings.github_client_id:
        raise HTTPException(status_code=404, detail="GitHub OAuth not configured")

    try:
        user_info = await exchange_github_code(code)
    except Exception:
        logger.exception("GitHub OAuth code exchange failed")
        raise HTTPException(status_code=400, detail="Failed to authenticate with GitHub")

    user = await get_or_create_oauth_user(
        db,
        provider="github",
        provider_id=user_info["provider_id"],
        email=user_info["email"],
        display_name=user_info.get("name"),
        avatar_url=user_info.get("picture"),
    )

    token = create_jwt(str(user.id), user.email)
    response = RedirectResponse(settings.auth_redirect_url, status_code=302)
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=7 * 24 * 60 * 60,  # 7 days
        path="/",
    )
    return response


# ---------------------------------------------------------------------------
# User profile / logout
# ---------------------------------------------------------------------------


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """Return the current authenticated user's profile."""
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "avatar_url": user.avatar_url,
        "provider": user.provider,
    }


@router.post("/logout")
async def logout():
    """Clear the auth cookie."""
    response = JSONResponse(content={"ok": True})
    response.delete_cookie(key="auth_token", path="/")
    return response
