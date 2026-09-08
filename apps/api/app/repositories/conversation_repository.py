import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.conversation import Conversation


async def get(db: AsyncSession, conversation_id: uuid.UUID) -> Conversation | None:
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    return result.scalar_one_or_none()


async def list_for_repository(
    db: AsyncSession, repository_id: uuid.UUID, *, limit: int = 50
) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.repository_id == repository_id)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


def create(
    db: AsyncSession, *, repository_id: uuid.UUID, created_by_user_id: uuid.UUID
) -> Conversation:
    conversation = Conversation(repository_id=repository_id, created_by_user_id=created_by_user_id)
    db.add(conversation)
    return conversation


def set_title(conversation: Conversation, title: str) -> None:
    conversation.title = title[:200]


def touch(conversation: Conversation, *, at: datetime) -> None:
    conversation.updated_at = at
