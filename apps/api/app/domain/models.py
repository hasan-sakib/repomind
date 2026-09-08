"""Aggregates all ORM model modules so Alembic autogenerate can see them,
and so string-based relationship() references between modules resolve."""

from app.domain.ai_run import AiRun
from app.domain.audit_log import AuditLog
from app.domain.branch import Branch
from app.domain.chat_status import (
    AiRunStatus,
    MessageFeedback,
    MessageRole,
    QueryIntent,
    RetrievalSourceType,
)
from app.domain.code_chunk import CodeChunk
from app.domain.code_embedding import CodeEmbedding
from app.domain.code_file import CodeFile
from app.domain.code_symbol import CodeSymbol
from app.domain.commit import Commit
from app.domain.conversation import Conversation
from app.domain.github_installation import GitHubInstallation
from app.domain.indexing_error import IndexingError
from app.domain.indexing_job import IndexingJob
from app.domain.indexing_status import IndexingJobStatus, IndexingStage, IndexingTrigger
from app.domain.issue import Issue
from app.domain.message import Message
from app.domain.organization import Organization
from app.domain.organization_member import OrganizationMember
from app.domain.pull_request import PullRequest
from app.domain.refresh_token import RefreshToken
from app.domain.repository import Repository
from app.domain.repository_membership import RepositoryMembership
from app.domain.repository_status import RepositoryStatus
from app.domain.retrieval_result import RetrievalResult
from app.domain.role import Role
from app.domain.session import Session
from app.domain.user import User
from app.domain.webhook_event import WebhookEvent

__all__ = [
    "AiRun",
    "AiRunStatus",
    "AuditLog",
    "Branch",
    "CodeChunk",
    "CodeEmbedding",
    "CodeFile",
    "CodeSymbol",
    "Commit",
    "Conversation",
    "GitHubInstallation",
    "IndexingError",
    "IndexingJob",
    "IndexingJobStatus",
    "IndexingStage",
    "IndexingTrigger",
    "Issue",
    "Message",
    "MessageFeedback",
    "MessageRole",
    "Organization",
    "OrganizationMember",
    "PullRequest",
    "QueryIntent",
    "RefreshToken",
    "Repository",
    "RepositoryMembership",
    "RepositoryStatus",
    "RetrievalResult",
    "RetrievalSourceType",
    "Role",
    "Session",
    "User",
    "WebhookEvent",
]
