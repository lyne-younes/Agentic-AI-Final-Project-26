"""Keeps a user's stored Google access token valid, refreshing it when it expires."""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import google
from app.models import User

REFRESH_MARGIN = timedelta(minutes=1)


async def get_valid_google_access_token(db: AsyncSession, user: User) -> str:
    if (
        user.google_access_token
        and user.token_expires_at
        and user.token_expires_at - REFRESH_MARGIN > datetime.now(UTC)
    ):
        return user.google_access_token

    if not user.google_refresh_token:
        raise google.GoogleOAuthError("No refresh token stored; the student must sign in again")

    tokens = await google.refresh_access_token(user.google_refresh_token)
    user.google_access_token = tokens.access_token
    user.token_expires_at = tokens.expires_at
    if tokens.refresh_token:
        user.google_refresh_token = tokens.refresh_token
    await db.commit()
    return tokens.access_token
