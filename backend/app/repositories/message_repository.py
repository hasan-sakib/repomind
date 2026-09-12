import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.chat_status import MessageFeedback, MessageRole
from app.domain.message import Message


async def get(db: AsyncSession, message_id: uuid.UUID) -> Message | None:
    return await db.get(Message, message_id)


async def list_for_conversation(db: AsyncSession, conversation_id: uuid.UUID) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())


def create(
    db: AsyncSession, *, conversation_id: uuid.UUID, role: MessageRole, content: str
) -> Message:
    message = Message(conversation_id=conversation_id, role=role, content=content)
    db.add(message)
    return message


def set_feedback(message: Message, feedback: MessageFeedback | None) -> None:
    message.feedback = feedback
