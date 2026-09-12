import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import (
    ChatProvider,
    ChatReranker,
    DbSession,
    QueryEmbeddingProvider,
    get_current_user,
    require_csrf_header,
    require_repository_access,
)
from app.core.config import get_settings
from app.models.repository import Repository
from app.models.user import User
from app.schemas.chat import (
    AskRequest,
    ChatStreamEvent,
    ConversationDetail,
    ConversationPublic,
    FeedbackRequest,
    MessagePublic,
)
from app.services import chat_service

router = APIRouter(prefix="/repositories/{repository_id}/conversations", tags=["chat"])


async def _sse(events: AsyncIterator[ChatStreamEvent]) -> AsyncIterator[str]:
    async for event in events:
        yield f"event: {event.type}\ndata: {event.model_dump_json()}\n\n"


@router.post("", response_model=ConversationPublic, status_code=201)
async def create_conversation(
    repository: Annotated[Repository, Depends(require_repository_access)],
    user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
) -> ConversationPublic:
    conversation = await chat_service.start_conversation(
        db, repository_id=repository.id, user_id=user.id
    )
    return ConversationPublic.from_conversation(conversation)


@router.get("", response_model=list[ConversationPublic])
async def list_conversations(
    repository: Annotated[Repository, Depends(require_repository_access)], db: DbSession
) -> list[ConversationPublic]:
    conversations = await chat_service.list_conversations(db, repository.id)
    return [ConversationPublic.from_conversation(c) for c in conversations]


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    repository: Annotated[Repository, Depends(require_repository_access)],
    conversation_id: uuid.UUID,
    db: DbSession,
) -> ConversationDetail:
    conversation = await chat_service.get_conversation_or_raise(
        db, repository_id=repository.id, conversation_id=conversation_id
    )
    messages = await chat_service.get_conversation_messages(
        db, conversation=conversation, repository_id=repository.id
    )
    return ConversationDetail(
        conversation=ConversationPublic.from_conversation(conversation), messages=messages
    )


@router.post(
    "/{conversation_id}/messages",
    dependencies=[Depends(require_csrf_header)],
)
async def ask(
    repository: Annotated[Repository, Depends(require_repository_access)],
    conversation_id: uuid.UUID,
    body: AskRequest,
    db: DbSession,
    ai_provider: ChatProvider,
    embedding_provider: QueryEmbeddingProvider,
    reranker: ChatReranker,
) -> StreamingResponse:
    conversation = await chat_service.get_conversation_or_raise(
        db, repository_id=repository.id, conversation_id=conversation_id
    )
    events = chat_service.ask(
        db,
        conversation=conversation,
        repository=repository,
        query=body.query,
        ai_provider=ai_provider,
        embedding_provider=embedding_provider,
        reranker=reranker,
        settings=get_settings(),
    )
    return StreamingResponse(_sse(events), media_type="text/event-stream")


@router.post(
    "/{conversation_id}/messages/{message_id}/regenerate",
    dependencies=[Depends(require_csrf_header)],
)
async def regenerate(
    repository: Annotated[Repository, Depends(require_repository_access)],
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    db: DbSession,
    ai_provider: ChatProvider,
    embedding_provider: QueryEmbeddingProvider,
    reranker: ChatReranker,
) -> StreamingResponse:
    conversation = await chat_service.get_conversation_or_raise(
        db, repository_id=repository.id, conversation_id=conversation_id
    )
    user_message = await chat_service.get_user_message_or_raise(
        db, conversation_id=conversation.id, message_id=message_id
    )
    events = chat_service.regenerate(
        db,
        conversation=conversation,
        repository=repository,
        user_message=user_message,
        ai_provider=ai_provider,
        embedding_provider=embedding_provider,
        reranker=reranker,
        settings=get_settings(),
    )
    return StreamingResponse(_sse(events), media_type="text/event-stream")


@router.patch(
    "/{conversation_id}/messages/{message_id}/feedback",
    response_model=MessagePublic,
    dependencies=[Depends(require_csrf_header)],
)
async def set_message_feedback(
    repository: Annotated[Repository, Depends(require_repository_access)],
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    body: FeedbackRequest,
    db: DbSession,
) -> MessagePublic:
    await chat_service.get_conversation_or_raise(
        db, repository_id=repository.id, conversation_id=conversation_id
    )
    message = await chat_service.get_message_or_raise(
        db, conversation_id=conversation_id, message_id=message_id
    )
    await chat_service.set_feedback(db, message=message, feedback=body.feedback)
    return MessagePublic.from_message(message)
