import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Cookie, Depends, Header, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.tokens import InvalidTokenError, decode_access_token
from app.db.session import get_db_session
from app.domain.organization_member import OrganizationMember
from app.domain.role import Role
from app.domain.session import Session
from app.domain.user import User
from app.repositories import session_repository, user_repository
from app.services import organization_service
from app.services.exceptions import CsrfError, NotAuthenticatedError

SESSION_COOKIE_NAME = "rm_session"
REFRESH_COOKIE_NAME = "rm_refresh"
CSRF_HEADER_VALUE = "RepoMind"

DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_user_and_session(
    db: DbSession,
    rm_session: Annotated[str | None, Cookie()] = None,
) -> tuple[User, Session]:
    if rm_session is None:
        raise NotAuthenticatedError("Not authenticated")

    try:
        payload = decode_access_token(rm_session)
    except InvalidTokenError as exc:
        raise NotAuthenticatedError("Invalid or expired session") from exc

    session_row = await session_repository.get_by_id(db, payload.session_id)
    now = datetime.now(UTC)
    if (
        session_row is None
        or session_row.revoked_at is not None
        or session_row.expires_at < now
        or session_row.user_id != payload.user_id
    ):
        raise NotAuthenticatedError("Invalid or expired session")

    user = await user_repository.get_by_id(db, payload.user_id)
    if user is None:
        raise NotAuthenticatedError("Invalid or expired session")

    return user, session_row


async def get_current_user(
    current: Annotated[tuple[User, Session], Depends(get_current_user_and_session)],
) -> User:
    return current[0]


def require_csrf_header(
    x_requested_with: Annotated[str | None, Header()] = None,
) -> None:
    """Mitigates CSRF on cookie-authenticated mutating requests: combined
    with SameSite=Lax cookies, a cross-site request can't set this custom
    header without triggering a CORS preflight our origin policy rejects.
    See docs/architecture/backend-architecture.md."""
    if x_requested_with != CSRF_HEADER_VALUE:
        raise CsrfError("Missing or invalid CSRF header")


def require_organization_role(
    minimum: Role,
) -> Callable[..., Awaitable[OrganizationMember]]:
    """Dependency factory: loads the caller's membership in the
    {organization_id} path param and enforces a minimum role. Raises the
    same not-found error whether the organization doesn't exist or the
    caller isn't a member of it — see
    organization_service.get_membership_or_raise."""

    async def dependency(
        db: DbSession,
        user: Annotated[User, Depends(get_current_user)],
        organization_id: Annotated[uuid.UUID, Path()],
    ) -> OrganizationMember:
        return await organization_service.require_role(
            db, organization_id=organization_id, user_id=user.id, minimum=minimum
        )

    return dependency
