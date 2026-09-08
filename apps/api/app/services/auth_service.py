import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security.password import hash_password, verify_password
from app.core.security.tokens import (
    create_access_token,
    generate_opaque_token,
    hash_opaque_token,
)
from app.domain.session import Session
from app.domain.user import User
from app.integrations.email.factory import get_email_sender
from app.integrations.github.oauth import GitHubUser
from app.repositories import (
    audit_log_repository,
    refresh_token_repository,
    session_repository,
    user_repository,
)
from app.services import organization_service
from app.services.exceptions import (
    EmailAlreadyRegisteredError,
    EmailNotVerifiedError,
    InvalidCredentialsError,
    InvalidOrExpiredTokenError,
)

settings = get_settings()


class AuthResult:
    __slots__ = ("user", "session", "access_token", "refresh_token")

    def __init__(self, user: User, session: Session, access_token: str, refresh_token: str):
        self.user = user
        self.session = session
        self.access_token = access_token
        self.refresh_token = refresh_token


async def _issue_session(
    db: AsyncSession, *, user: User, ip_address: str | None, user_agent: str | None
) -> tuple[Session, str, str]:
    now = datetime.now(UTC)
    session_row = session_repository.create(
        db,
        user_id=user.id,
        expires_at=now + timedelta(days=settings.refresh_token_ttl_days),
        last_used_at=now,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    await db.flush()

    raw_refresh_token = generate_opaque_token()
    refresh_token_repository.create(
        db,
        session_id=session_row.id,
        token_hash=hash_opaque_token(raw_refresh_token),
        expires_at=now + timedelta(days=settings.refresh_token_ttl_days),
    )
    access_token = create_access_token(user_id=user.id, session_id=session_row.id)
    return session_row, access_token, raw_refresh_token


async def _send_verification_email(user: User) -> None:
    raw_token = generate_opaque_token()
    user.email_verification_token_hash = hash_opaque_token(raw_token)
    user.email_verification_expires_at = datetime.now(UTC) + timedelta(
        hours=settings.email_verification_token_ttl_hours
    )
    link = f"{settings.frontend_url}/verify-email?token={raw_token}"
    await get_email_sender().send(
        to=user.email,
        subject="Verify your RepoMind email",
        body=f"Confirm your email address: {link}\n\nThis link expires in "
        f"{settings.email_verification_token_ttl_hours} hours.",
    )


async def register(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str,
    ip_address: str | None,
    user_agent: str | None,
) -> AuthResult:
    if await user_repository.get_by_email(db, email) is not None:
        raise EmailAlreadyRegisteredError("An account with this email already exists")

    user = user_repository.create(
        db, email=email, full_name=full_name, password_hash=hash_password(password)
    )
    await db.flush()

    await organization_service.create_organization(db, name=full_name, owner=user)
    await _send_verification_email(user)

    audit_log_repository.create(
        db, action="user.registered", actor_user_id=user.id, ip_address=ip_address
    )
    session_row, access_token, raw_refresh_token = await _issue_session(
        db, user=user, ip_address=ip_address, user_agent=user_agent
    )
    await db.commit()
    await db.refresh(user)
    return AuthResult(user, session_row, access_token, raw_refresh_token)


async def login(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    ip_address: str | None,
    user_agent: str | None,
) -> AuthResult:
    user = await user_repository.get_by_email(db, email)
    if (
        user is None
        or user.password_hash is None
        or not verify_password(password, user.password_hash)
    ):
        raise InvalidCredentialsError("Invalid email or password")

    if settings.require_email_verification and user.email_verified_at is None:
        raise EmailNotVerifiedError("Please verify your email before logging in")

    audit_log_repository.create(
        db, action="user.login", actor_user_id=user.id, ip_address=ip_address
    )
    session_row, access_token, raw_refresh_token = await _issue_session(
        db, user=user, ip_address=ip_address, user_agent=user_agent
    )
    await db.commit()
    return AuthResult(user, session_row, access_token, raw_refresh_token)


async def login_with_github(
    db: AsyncSession,
    *,
    github_user: GitHubUser,
    email: str | None,
    ip_address: str | None,
    user_agent: str | None,
) -> AuthResult:
    user = await user_repository.get_by_github_user_id(db, github_user.id)
    if user is None:
        if not email:
            raise InvalidCredentialsError(
                "Your GitHub account has no verified public email RepoMind can use. "
                "Make an email public and verified on GitHub, or register with a password."
            )
        user = user_repository.create(
            db,
            email=email,
            full_name=github_user.name or github_user.login,
            github_user_id=github_user.id,
            avatar_url=github_user.avatar_url,
        )
        await db.flush()
        await organization_service.create_organization(
            db, name=github_user.name or github_user.login, owner=user
        )
        # GitHub already verified this email address.
        user.email_verified_at = datetime.now(UTC)
        audit_log_repository.create(
            db,
            action="user.registered",
            actor_user_id=user.id,
            ip_address=ip_address,
            extra={"provider": "github"},
        )

    audit_log_repository.create(
        db,
        action="user.login",
        actor_user_id=user.id,
        ip_address=ip_address,
        extra={"provider": "github"},
    )
    session_row, access_token, raw_refresh_token = await _issue_session(
        db, user=user, ip_address=ip_address, user_agent=user_agent
    )
    await db.commit()
    await db.refresh(user)
    return AuthResult(user, session_row, access_token, raw_refresh_token)


async def refresh_session(db: AsyncSession, *, raw_refresh_token: str) -> tuple[str, str]:
    """Returns (new_access_token, new_raw_refresh_token). Rotates the
    refresh token on every use; presenting an already-rotated token revokes
    the whole session (theft indicator) — see docs/architecture/backend-architecture.md."""
    token_hash = hash_opaque_token(raw_refresh_token)
    token = await refresh_token_repository.get_by_token_hash(db, token_hash)
    if token is None:
        raise InvalidOrExpiredTokenError("Invalid refresh token")

    now = datetime.now(UTC)
    session_row = await session_repository.get_by_id(db, token.session_id)

    if token.revoked_at is not None or session_row is None:
        if session_row is not None:
            session_repository.revoke(session_row, at=now)
            await db.commit()
        raise InvalidOrExpiredTokenError("Refresh token has already been used")

    if token.expires_at < now or session_row.revoked_at is not None or session_row.expires_at < now:
        raise InvalidOrExpiredTokenError("Refresh token or session has expired")

    refresh_token_repository.revoke(token, at=now)
    new_raw_refresh_token = generate_opaque_token()
    refresh_token_repository.create(
        db,
        session_id=session_row.id,
        token_hash=hash_opaque_token(new_raw_refresh_token),
        expires_at=session_row.expires_at,
    )
    session_repository.touch(session_row, at=now)
    new_access_token = create_access_token(user_id=session_row.user_id, session_id=session_row.id)
    await db.commit()
    return new_access_token, new_raw_refresh_token


async def logout(db: AsyncSession, *, session_id: uuid.UUID, user_id: uuid.UUID) -> None:
    session_row = await session_repository.get_by_id(db, session_id)
    if session_row is not None and session_row.revoked_at is None:
        session_repository.revoke(session_row, at=datetime.now(UTC))
        audit_log_repository.create(db, action="user.logout", actor_user_id=user_id)
        await db.commit()


async def request_password_reset(db: AsyncSession, *, email: str) -> None:
    """Always succeeds from the caller's perspective, whether or not the
    email is registered — avoids leaking which emails have accounts."""
    user = await user_repository.get_by_email(db, email)
    if user is None:
        return

    raw_token = generate_opaque_token()
    user.password_reset_token_hash = hash_opaque_token(raw_token)
    user.password_reset_expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.password_reset_token_ttl_minutes
    )
    link = f"{settings.frontend_url}/reset-password?token={raw_token}"
    await get_email_sender().send(
        to=user.email,
        subject="Reset your RepoMind password",
        body=f"Reset your password: {link}\n\nThis link expires in "
        f"{settings.password_reset_token_ttl_minutes} minutes. "
        "If you didn't request this, you can ignore this email.",
    )
    audit_log_repository.create(db, action="user.password_reset_requested", actor_user_id=user.id)
    await db.commit()


async def confirm_password_reset(db: AsyncSession, *, token: str, new_password: str) -> None:
    token_hash = hash_opaque_token(token)
    user = await user_repository.get_by_password_reset_token_hash(db, token_hash)
    now = datetime.now(UTC)
    if (
        user is None
        or user.password_reset_expires_at is None
        or user.password_reset_expires_at < now
    ):
        raise InvalidOrExpiredTokenError("Invalid or expired password reset link")

    user.password_hash = hash_password(new_password)
    user.password_reset_token_hash = None
    user.password_reset_expires_at = None

    for session_row in await session_repository.list_active_for_user(db, user.id):
        session_repository.revoke(session_row, at=now)

    audit_log_repository.create(db, action="user.password_reset_completed", actor_user_id=user.id)
    await db.commit()


async def request_email_verification(db: AsyncSession, *, user: User) -> None:
    await _send_verification_email(user)
    await db.commit()


async def confirm_email_verification(db: AsyncSession, *, token: str) -> User:
    token_hash = hash_opaque_token(token)
    user = await user_repository.get_by_email_verification_token_hash(db, token_hash)
    now = datetime.now(UTC)
    if (
        user is None
        or user.email_verification_expires_at is None
        or user.email_verification_expires_at < now
    ):
        raise InvalidOrExpiredTokenError("Invalid or expired verification link")

    user.email_verified_at = now
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    audit_log_repository.create(db, action="user.email_verified", actor_user_id=user.id)
    await db.commit()
    await db.refresh(user)
    return user
