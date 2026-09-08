import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import get_settings

settings = get_settings()

ACCESS_TOKEN_TYPE = "access"


class InvalidTokenError(Exception):
    """Raised when a JWT is malformed, expired, or otherwise not honored."""


@dataclass(frozen=True, slots=True)
class AccessTokenPayload:
    user_id: uuid.UUID
    session_id: uuid.UUID


def create_access_token(user_id: uuid.UUID, session_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> AccessTokenPayload:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise InvalidTokenError("Unexpected token type")

    try:
        return AccessTokenPayload(
            user_id=uuid.UUID(payload["sub"]), session_id=uuid.UUID(payload["sid"])
        )
    except (KeyError, ValueError) as exc:
        raise InvalidTokenError("Malformed token claims") from exc


def generate_opaque_token() -> str:
    """A high-entropy, URL-safe token to hand to the client (refresh token,
    password reset link, email verification link). Only its hash is stored
    server-side — see hash_opaque_token."""
    return secrets.token_urlsafe(32)


def hash_opaque_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
