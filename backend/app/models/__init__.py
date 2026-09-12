"""Aggregates all ORM model modules so Alembic autogenerate can see them,
and so string-based relationship() references between modules resolve."""

from app.models.ai_run import AiRun
from app.models.analytics_snapshot import AnalyticsSnapshot
from app.models.analytics_status import AnalyticsSnapshotStatus
from app.models.audit_log import AuditLog
from app.models.branch import Branch
from app.models.chat_status import (
    AiRunStatus,
    MessageFeedback,
    MessageRole,
    QueryIntent,
    RetrievalSourceType,
)
from app.models.code_chunk import CodeChunk
from app.models.code_embedding import CodeEmbedding
from app.models.code_file import CodeFile
from app.models.code_symbol import CodeSymbol
from app.models.commit import Commit
from app.models.conversation import Conversation
from app.models.github_installation import GitHubInstallation
from app.models.indexing_error import IndexingError
from app.models.indexing_job import IndexingJob
from app.models.indexing_status import IndexingJobStatus, IndexingStage, IndexingTrigger
from app.models.issue import Issue
from app.models.message import Message
from app.models.onboarding_guide import OnboardingGuide
from app.models.onboarding_progress import OnboardingProgress
from app.models.onboarding_status import OnboardingGuideStatus
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.pr_analysis_status import PRAnalysisStatus, PRRiskLevel
from app.models.pull_request import PullRequest
from app.models.pull_request_analysis import PullRequestAnalysis
from app.models.refresh_token import RefreshToken
from app.models.repository import Repository
from app.models.repository_membership import RepositoryMembership
from app.models.repository_status import RepositoryStatus
from app.models.retrieval_result import RetrievalResult
from app.models.role import Role
from app.models.session import Session
from app.models.user import User
from app.models.webhook_event import WebhookEvent

__all__ = [
    "AiRun",
    "AiRunStatus",
    "AnalyticsSnapshot",
    "AnalyticsSnapshotStatus",
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
    "OnboardingGuide",
    "OnboardingGuideStatus",
    "OnboardingProgress",
    "Organization",
    "OrganizationMember",
    "PRAnalysisStatus",
    "PRRiskLevel",
    "PullRequest",
    "PullRequestAnalysis",
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
