"""OAuth / JWT authentication helpers.

Uses python-jose for JWT and httpx for OAuth provider HTTP calls.
"""

import logging
from datetime import datetime, timedelta, timezone

import httpx
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import User

logger = logging.getLogger(__name__)

_ALGORITHM = "HS256"
_TOKEN_EXPIRE_DAYS = 7

# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------


def create_jwt(user_id: str, email: str) -> str:
    """Create a signed JWT token with 7-day expiry."""
    expire = datetime.now(timezone.utc) + timedelta(days=_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "email": email,
        "exp": expire,
    }
    return jwt.encode(payload, settings.auth_secret, algorithm=_ALGORITHM)


def verify_jwt(token: str) -> dict | None:
    """Verify and decode a JWT token. Returns payload dict or None if invalid."""
    try:
        payload = jwt.decode(token, settings.auth_secret, algorithms=[_ALGORITHM])
        user_id: str | None = payload.get("sub")
        email: str | None = payload.get("email")
        if user_id is None or email is None:
            return None
        return {"user_id": user_id, "email": email}
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


async def get_or_create_oauth_user(
    db: AsyncSession,
    provider: str,
    provider_id: str,
    email: str,
    display_name: str | None,
    avatar_url: str | None,
) -> User:
    """Find an existing user by provider+provider_id, or create a new one."""
    # First try to find by provider + provider_id
    result = await db.execute(
        select(User).where(User.provider == provider, User.provider_id == provider_id)
    )
    user = result.scalar_one_or_none()

    if user:
        # Update profile fields in case they changed
        user.display_name = display_name or user.display_name
        user.avatar_url = avatar_url or user.avatar_url
        user.email = email
        await db.commit()
        await db.refresh(user)
        return user

    # Check if a user with the same email already exists (link accounts)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user and user.provider == "anonymous":
        # Upgrade anonymous user to OAuth user
        user.provider = provider
        user.provider_id = provider_id
        user.display_name = display_name or user.display_name
        user.avatar_url = avatar_url or user.avatar_url
        await db.commit()
        await db.refresh(user)
        return user

    # Create new user
    user = User(
        email=email,
        display_name=display_name,
        avatar_url=avatar_url,
        provider=provider,
        provider_id=provider_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# OAuth provider code exchange
# ---------------------------------------------------------------------------


async def exchange_google_code(code: str) -> dict:
    """Exchange a Google OAuth authorization code for user info.

    Returns dict with keys: email, name, picture, provider_id.
    """
    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": f"{settings.auth_redirect_url}/api/v1/auth/callback/google",
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data["access_token"]

        # Fetch user info
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        userinfo_resp.raise_for_status()
        userinfo = userinfo_resp.json()

    return {
        "email": userinfo["email"],
        "name": userinfo.get("name"),
        "picture": userinfo.get("picture"),
        "provider_id": userinfo["id"],
    }


async def exchange_github_code(code: str) -> dict:
    """Exchange a GitHub OAuth authorization code for user info.

    Returns dict with keys: email, name, picture, provider_id.
    """
    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            data={
                "code": code,
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
            },
            headers={"Accept": "application/json"},
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data["access_token"]

        # Fetch user info
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/vnd.github+json",
            },
        )
        user_resp.raise_for_status()
        user_data = user_resp.json()

        # GitHub may not return email from /user if it's private; fetch from /user/emails
        email = user_data.get("email")
        if not email:
            emails_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            emails_resp.raise_for_status()
            emails = emails_resp.json()
            primary = next((e for e in emails if e.get("primary")), emails[0] if emails else None)
            email = primary["email"] if primary else f"{user_data['id']}@users.noreply.github.com"

    return {
        "email": email,
        "name": user_data.get("name") or user_data.get("login"),
        "picture": user_data.get("avatar_url"),
        "provider_id": str(user_data["id"]),
    }
