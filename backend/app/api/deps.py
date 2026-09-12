import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Annotated

from arq.connections import ArqRedis
from fastapi import Cookie, Depends, Header, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embedding_provider import EmbeddingProvider
from app.ai.factory import get_ai_provider, get_embedding_provider, get_reranker
from app.ai.provider import AIProvider
from app.ai.reranker import Reranker
from app.core.security.tokens import InvalidTokenError, decode_access_token
from app.db.session import get_db_session
from app.models.organization_member import OrganizationMember
from app.models.repository import Repository
from app.models.role import Role
from app.models.session import Session
from app.models.user import User
from app.repositories import session_repository, user_repository
from app.services import organization_service, repository_service
from app.services.exceptions import CsrfError, NotAuthenticatedError

SESSION_COOKIE_NAME = "rm_session"
REFRESH_COOKIE_NAME = "rm_refresh"
CSRF_HEADER_VALUE = "RepoMind"

DbSession = Annotated[AsyncSession, Depends(get_db_session)]

# AIProvider/EmbeddingProvider/Reranker are process-wide singletons
# (@lru_cache in app/ai/factory.py) wrapped as dependencies purely so
# route handlers can depend on the abstraction and tests can override
# them — matches the ArqPool/DbSession pattern below.
ChatProvider = Annotated[AIProvider, Depends(get_ai_provider)]
QueryEmbeddingProvider = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]
ChatReranker = Annotated[Reranker, Depends(get_reranker)]


def get_arq_pool(request: Request) -> ArqRedis:
    """The arq Redis pool created once in the FastAPI lifespan (app/main.py)
    — not a per-request connection."""
    pool: ArqRedis = request.app.state.arq_pool
    return pool


ArqPool = Annotated[ArqRedis, Depends(get_arq_pool)]


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


async def require_repository_access(
    db: DbSession,
    user: Annotated[User, Depends(get_current_user)],
    repository_id: Annotated[uuid.UUID, Path()],
) -> Repository:
    """Loads the {repository_id} path param, enforcing that the caller has
    a RepositoryMembership row for it — see
    repository_service.require_repository_access."""
    return await repository_service.require_repository_access(
        db, repository_id=repository_id, user_id=user.id
    )
