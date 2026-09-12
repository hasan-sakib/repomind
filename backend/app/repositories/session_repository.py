import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session


async def get_by_id(db: AsyncSession, session_id: uuid.UUID) -> Session | None:
    return await db.get(Session, session_id)


async def list_active_for_user(db: AsyncSession, user_id: uuid.UUID) -> list[Session]:
    result = await db.execute(
        select(Session).where(Session.user_id == user_id, Session.revoked_at.is_(None))
    )
    return list(result.scalars().all())


def create(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    expires_at: datetime,
    last_used_at: datetime,
    user_agent: str | None,
    ip_address: str | None,
) -> Session:
    session_row = Session(
        user_id=user_id,
        expires_at=expires_at,
        last_used_at=last_used_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    db.add(session_row)
    return session_row


def revoke(session_row: Session, *, at: datetime) -> None:
    session_row.revoked_at = at


def touch(session_row: Session, *, at: datetime) -> None:
    session_row.last_used_at = at
