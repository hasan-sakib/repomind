import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.domain.chat_status import MessageFeedback, MessageRole, QueryIntent, RetrievalSourceType
from app.domain.conversation import Conversation
from app.domain.message import Message
from app.domain.retrieval_result import RetrievalResult


class SourceReferencePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_type: RetrievalSourceType
    rank: int
    score: float | None
    file_path: str | None
    start_line: int | None
    end_line: int | None
    symbol_name: str | None
    commit_sha: str | None
    commit_url: str | None = None

    @classmethod
    def from_result(
        cls, result: RetrievalResult, *, commit_url: str | None = None
    ) -> "SourceReferencePublic":
        return cls(
            source_type=result.source_type,
            rank=result.rank,
            score=result.score,
            file_path=result.file_path,
            start_line=result.start_line,
            end_line=result.end_line,
            symbol_name=result.symbol_name,
            commit_sha=result.commit_sha,
            commit_url=commit_url,
        )


class MessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: MessageRole
    content: str
    feedback: MessageFeedback | None
    created_at: datetime
    intent: QueryIntent | None = None
    sources: list[SourceReferencePublic] = Field(default_factory=list)

    @classmethod
    def from_message(
        cls,
        message: Message,
        *,
        intent: QueryIntent | None = None,
        sources: list[SourceReferencePublic] | None = None,
    ) -> "MessagePublic":
        return cls(
            id=message.id,
            role=message.role,
            content=message.content,
            feedback=message.feedback,
            created_at=message.created_at,
            intent=intent,
            sources=sources or [],
        )


class ConversationPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    repository_id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_conversation(cls, conversation: Conversation) -> "ConversationPublic":
        return cls.model_validate(conversation)


class ConversationDetail(BaseModel):
    conversation: ConversationPublic
    messages: list[MessagePublic]


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=4000)


class FeedbackRequest(BaseModel):
    feedback: MessageFeedback | None


class SourcesEvent(BaseModel):
    """First SSE event for a query — sent as soon as retrieval + ranking
    finish, before the LLM call starts, since sources don't depend on
    generation. Lets the frontend populate the source panel immediately."""

    type: Literal["sources"] = "sources"
    sources: list[SourceReferencePublic]


class TokenEvent(BaseModel):
    type: Literal["token"] = "token"
    text: str


class DoneEvent(BaseModel):
    type: Literal["done"] = "done"
    message_id: uuid.UUID
    run_id: uuid.UUID


class ErrorEvent(BaseModel):
    type: Literal["error"] = "error"
    message: str


ChatStreamEvent = SourcesEvent | TokenEvent | DoneEvent | ErrorEvent
