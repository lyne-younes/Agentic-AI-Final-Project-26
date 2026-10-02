from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.sessions import SESSION_COOKIE, unsign_session_id
from app.db import get_db
from app.models import User, UserSession

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(request: Request, db: DbSession) -> User:
    session_id = unsign_session_id(request.cookies.get(SESSION_COOKIE))
    if session_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    user = await db.scalar(
        select(User)
        .join(UserSession, UserSession.user_id == User.id)
        .where(UserSession.id == session_id, UserSession.expires_at > func.now())
    )
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
