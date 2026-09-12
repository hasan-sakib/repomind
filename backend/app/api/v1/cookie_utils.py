from fastapi import Response

from app.api.deps import REFRESH_COOKIE_NAME, SESSION_COOKIE_NAME
from app.core.config import get_settings

settings = get_settings()


def _secure() -> bool:
    return settings.environment == "production"


def set_session_cookies(response: Response, *, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        access_token,
        max_age=settings.access_token_ttl_minutes * 60,
        httponly=True,
        secure=_secure(),
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh_token,
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=_secure(),
        samesite="lax",
        path=f"{settings.api_v1_prefix}/auth/refresh",
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    response.delete_cookie(REFRESH_COOKIE_NAME, path=f"{settings.api_v1_prefix}/auth/refresh")
