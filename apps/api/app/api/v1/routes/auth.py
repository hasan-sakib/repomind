import secrets
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Query, Request, Response
from fastapi.responses import RedirectResponse

from app.api.deps import (
    DbSession,
    get_current_user,
    get_current_user_and_session,
    require_csrf_header,
)
from app.api.v1.cookie_utils import clear_session_cookies, set_session_cookies
from app.core.config import get_settings
from app.domain.session import Session
from app.domain.user import User
from app.integrations.github import oauth as github_oauth
from app.schemas.auth import (
    AuthResponse,
    EmailVerificationConfirmRequest,
    LoginRequest,
    MeResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequestRequest,
    RegisterRequest,
)
from app.schemas.organization import OrganizationMembershipPublic
from app.schemas.user import UserPublic
from app.services import auth_service, organization_service
from app.services.exceptions import GitHubAuthError, NotAuthenticatedError

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

GITHUB_STATE_COOKIE = "rm_github_oauth_state"


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _github_redirect_uri(request: Request) -> str:
    return f"{str(request.base_url).rstrip('/')}{settings.api_v1_prefix}/auth/github/callback"


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(
    body: RegisterRequest, request: Request, response: Response, db: DbSession
) -> AuthResponse:
    result = await auth_service.register(
        db,
        email=body.email,
        password=body.password,
        full_name=body.full_name,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    set_session_cookies(
        response, access_token=result.access_token, refresh_token=result.refresh_token
    )
    return AuthResponse(user=UserPublic.from_user(result.user))


@router.post("/login", response_model=AuthResponse)
async def login(
    body: LoginRequest, request: Request, response: Response, db: DbSession
) -> AuthResponse:
    result = await auth_service.login(
        db,
        email=body.email,
        password=body.password,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    set_session_cookies(
        response, access_token=result.access_token, refresh_token=result.refresh_token
    )
    return AuthResponse(user=UserPublic.from_user(result.user))


@router.post("/logout", status_code=204, dependencies=[Depends(require_csrf_header)])
async def logout(
    response: Response,
    db: DbSession,
    current: Annotated[tuple[User, Session], Depends(get_current_user_and_session)],
) -> None:
    user, session_row = current
    await auth_service.logout(db, session_id=session_row.id, user_id=user.id)
    clear_session_cookies(response)


@router.post("/refresh", status_code=204)
async def refresh(
    response: Response,
    db: DbSession,
    rm_refresh: Annotated[str | None, Cookie()] = None,
) -> None:
    if rm_refresh is None:
        raise NotAuthenticatedError("No refresh token presented")

    new_access_token, new_refresh_token = await auth_service.refresh_session(
        db, raw_refresh_token=rm_refresh
    )
    set_session_cookies(
        response, access_token=new_access_token, refresh_token=new_refresh_token
    )


@router.get("/me", response_model=MeResponse)
async def me(db: DbSession, user: Annotated[User, Depends(get_current_user)]) -> MeResponse:
    memberships = await organization_service.list_organizations_for_user(db, user.id)
    return MeResponse(
        user=UserPublic.from_user(user),
        organizations=[OrganizationMembershipPublic.from_member(m) for m in memberships],
    )


@router.post("/password-reset/request", status_code=204)
async def request_password_reset(body: PasswordResetRequestRequest, db: DbSession) -> None:
    await auth_service.request_password_reset(db, email=body.email)


@router.post("/password-reset/confirm", status_code=204)
async def confirm_password_reset(body: PasswordResetConfirmRequest, db: DbSession) -> None:
    await auth_service.confirm_password_reset(
        db, token=body.token, new_password=body.new_password
    )


@router.post(
    "/email/verify/request", status_code=204, dependencies=[Depends(require_csrf_header)]
)
async def request_email_verification(
    db: DbSession, user: Annotated[User, Depends(get_current_user)]
) -> None:
    await auth_service.request_email_verification(db, user=user)


@router.post("/email/verify/confirm", response_model=UserPublic)
async def confirm_email_verification(
    body: EmailVerificationConfirmRequest, db: DbSession
) -> UserPublic:
    user = await auth_service.confirm_email_verification(db, token=body.token)
    return UserPublic.from_user(user)


@router.get("/github/login")
async def github_login(request: Request) -> RedirectResponse:
    state = secrets.token_urlsafe(24)
    redirect = RedirectResponse(
        github_oauth.build_authorize_url(
            redirect_uri=_github_redirect_uri(request), state=state
        )
    )
    redirect.set_cookie(
        GITHUB_STATE_COOKIE,
        state,
        max_age=600,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        path=f"{settings.api_v1_prefix}/auth/github/callback",
    )
    return redirect


@router.get("/github/callback")
async def github_callback(
    request: Request,
    db: DbSession,
    code: Annotated[str, Query()],
    state: Annotated[str, Query()],
    rm_github_oauth_state: Annotated[str | None, Cookie()] = None,
) -> RedirectResponse:
    if rm_github_oauth_state is None or not secrets.compare_digest(state, rm_github_oauth_state):
        raise GitHubAuthError("Invalid OAuth state")

    redirect_uri = _github_redirect_uri(request)
    access_token = await github_oauth.exchange_code_for_access_token(
        code=code, redirect_uri=redirect_uri
    )
    github_user = await github_oauth.fetch_github_user(access_token)
    email = await github_oauth.fetch_github_primary_email(access_token)

    result = await auth_service.login_with_github(
        db,
        github_user=github_user,
        email=email,
        ip_address=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )

    redirect = RedirectResponse(f"{settings.frontend_url}/dashboard")
    set_session_cookies(
        redirect, access_token=result.access_token, refresh_token=result.refresh_token
    )
    redirect.delete_cookie(
        GITHUB_STATE_COOKIE, path=f"{settings.api_v1_prefix}/auth/github/callback"
    )
    return redirect
