"""Google OAuth 2.0 client: consent URL, code exchange, token refresh, profile lookup."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx

from app.config import get_settings

AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

CALENDAR_SCOPES = (
    "https://www.googleapis.com/auth/calendar.readonly",  # exams/deadlines + free/busy
    "https://www.googleapis.com/auth/calendar.events",  # write confirmed study sessions
)
# Identity and Calendar access are requested together in a single consent step.
SCOPES = ("openid", "email", "profile", *CALENDAR_SCOPES)


class GoogleOAuthError(Exception):
    pass


@dataclass(frozen=True)
class GoogleTokens:
    access_token: str
    refresh_token: str | None
    expires_at: datetime
    scopes: frozenset[str]

    @property
    def has_calendar_access(self) -> bool:
        return self.scopes.issuperset(CALENDAR_SCOPES)


@dataclass(frozen=True)
class GoogleProfile:
    google_id: str
    email: str
    name: str


def build_authorization_url(state: str) -> str:
    settings = get_settings()
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
        # Always return a refresh token, so Calendar access keeps working.
        "access_type": "offline",
        "prompt": "consent",
    }
    return f"{AUTHORIZATION_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> GoogleTokens:
    return await _request_tokens(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": get_settings().google_redirect_uri,
        }
    )


async def refresh_access_token(refresh_token: str) -> GoogleTokens:
    return await _request_tokens({"grant_type": "refresh_token", "refresh_token": refresh_token})


async def fetch_profile(access_token: str) -> GoogleProfile:
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(
                USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
            )
        except httpx.HTTPError as exc:
            raise GoogleOAuthError("Could not reach Google") from exc
    if response.status_code != 200:
        raise GoogleOAuthError(f"Profile request failed ({response.status_code})")
    data = response.json()
    return GoogleProfile(
        google_id=data["sub"], email=data["email"], name=data.get("name") or data["email"]
    )


async def _request_tokens(payload: dict[str, str]) -> GoogleTokens:
    settings = get_settings()
    payload = {
        **payload,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
    }
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.post(TOKEN_URL, data=payload)
        except httpx.HTTPError as exc:
            raise GoogleOAuthError("Could not reach Google") from exc
    if response.status_code != 200:
        raise GoogleOAuthError(f"Token request failed ({response.status_code}): {response.text}")
    data = response.json()
    return GoogleTokens(
        access_token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        expires_at=datetime.now(UTC) + timedelta(seconds=int(data["expires_in"])),
        scopes=frozenset(data.get("scope", "").split()),
    )
