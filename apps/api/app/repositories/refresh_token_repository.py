import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.refresh_token import RefreshToken


async def get_by_token_hash(db: AsyncSession, token_hash: str) -> RefreshToken | None:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    return result.scalar_one_or_none()


def create(
    db: AsyncSession, *, session_id: uuid.UUID, token_hash: str, expires_at: datetime
) -> RefreshToken:
    token = RefreshToken(session_id=session_id, token_hash=token_hash, expires_at=expires_at)
    db.add(token)
    return token


def revoke(token: RefreshToken, *, at: datetime) -> None:
    token.revoked_at = at
