"""Server-side sessions referenced by an HTTP-only signed cookie."""

import secrets
from datetime import UTC, datetime, timedelta

from fastapi import Response
from itsdangerous import BadSignature, URLSafeSerializer, URLSafeTimedSerializer
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import UserSession

SESSION_COOKIE = "session"
STATE_COOKIE = "oauth_state"
STATE_MAX_AGE_SECONDS = 600


def _session_serializer() -> URLSafeSerializer:
    return URLSafeSerializer(get_settings().secret_key, salt="session")


def _state_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt="oauth-state")


def create_session(db: AsyncSession, user_id: int) -> UserSession:
    ttl = timedelta(days=get_settings().session_ttl_days)
    session = UserSession(
        id=secrets.token_urlsafe(32), user_id=user_id, expires_at=datetime.now(UTC) + ttl
    )
    db.add(session)
    return session


async def delete_session(db: AsyncSession, session_id: str) -> None:
    await db.execute(delete(UserSession).where(UserSession.id == session_id))


def sign_session_id(session_id: str) -> str:
    return _session_serializer().dumps(session_id)


def unsign_session_id(cookie_value: str | None) -> str | None:
    if not cookie_value:
        return None
    try:
        return _session_serializer().loads(cookie_value)
    except BadSignature:
        return None


def set_session_cookie(response: Response, session: UserSession) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        sign_session_id(session.id),
        max_age=settings.session_ttl_days * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        SESSION_COOKIE, httponly=True, samesite="lax", secure=get_settings().cookie_secure
    )


def sign_state(state: str) -> str:
    return _state_serializer().dumps(state)


def unsign_state(cookie_value: str | None) -> str | None:
    if not cookie_value:
        return None
    try:
        return _state_serializer().loads(cookie_value, max_age=STATE_MAX_AGE_SECONDS)
    except BadSignature:  # also covers SignatureExpired
        return None


def set_state_cookie(response: Response, state: str) -> None:
    response.set_cookie(
        STATE_COOKIE,
        sign_state(state),
        max_age=STATE_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",  # sent on Google's top-level redirect back to the callback
        secure=get_settings().cookie_secure,
    )


def clear_state_cookie(response: Response) -> None:
    response.delete_cookie(
        STATE_COOKIE, httponly=True, samesite="lax", secure=get_settings().cookie_secure
    )
