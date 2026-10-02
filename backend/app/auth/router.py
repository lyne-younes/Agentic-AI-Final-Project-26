import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.auth import google
from app.auth.dependencies import CurrentUser, DbSession
from app.auth.sessions import (
    SESSION_COOKIE,
    STATE_COOKIE,
    clear_session_cookie,
    clear_state_cookie,
    create_session,
    delete_session,
    set_session_cookie,
    set_state_cookie,
    unsign_session_id,
    unsign_state,
)
from app.config import get_settings
from app.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str


@router.get("/login")
async def login() -> RedirectResponse:
    state = secrets.token_urlsafe(32)
    response = RedirectResponse(google.build_authorization_url(state))
    set_state_cookie(response, state)
    return response


@router.get("/callback")
async def callback(
    request: Request,
    db: DbSession,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
) -> RedirectResponse:
    expected_state = unsign_state(request.cookies.get(STATE_COOKIE))
    if (
        error
        or not code
        or not state
        or expected_state is None
        or not secrets.compare_digest(state, expected_state)
    ):
        return _redirect_to_login("oauth_failed")

    try:
        tokens = await google.exchange_code(code)
        if not tokens.has_calendar_access:
            # The student unticked the Calendar permission on Google's consent screen.
            return _redirect_to_login("calendar_access_required")
        profile = await google.fetch_profile(tokens.access_token)
    except google.GoogleOAuthError:
        return _redirect_to_login("oauth_failed")

    user = await db.scalar(select(User).where(User.google_id == profile.google_id))
    if user is None:
        user = User(google_id=profile.google_id)
        db.add(user)
    user.email = profile.email
    user.name = profile.name
    user.google_access_token = tokens.access_token
    user.token_expires_at = tokens.expires_at
    if tokens.refresh_token:
        user.google_refresh_token = tokens.refresh_token
    await db.flush()

    session = create_session(db, user.id)
    await db.commit()

    response = RedirectResponse(f"{get_settings().app_url}/courses")
    set_session_cookie(response, session)
    clear_state_cookie(response)
    return response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, db: DbSession) -> None:
    session_id = unsign_session_id(request.cookies.get(SESSION_COOKIE))
    if session_id is not None:
        await delete_session(db, session_id)
        await db.commit()
    clear_session_cookie(response)


@router.get("/me")
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)


def _redirect_to_login(error: str) -> RedirectResponse:
    response = RedirectResponse(f"{get_settings().app_url}/login?{urlencode({'error': error})}")
    clear_state_cookie(response)
    return response
