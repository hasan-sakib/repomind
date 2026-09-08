"""Aggregates all ORM model modules so Alembic autogenerate can see them,
and so string-based relationship() references between modules resolve."""

from app.domain.audit_log import AuditLog
from app.domain.branch import Branch
from app.domain.commit import Commit
from app.domain.github_installation import GitHubInstallation
from app.domain.issue import Issue
from app.domain.organization import Organization
from app.domain.organization_member import OrganizationMember
from app.domain.pull_request import PullRequest
from app.domain.refresh_token import RefreshToken
from app.domain.repository import Repository
from app.domain.repository_membership import RepositoryMembership
from app.domain.repository_status import RepositoryStatus
from app.domain.role import Role
from app.domain.session import Session
from app.domain.user import User
from app.domain.webhook_event import WebhookEvent

__all__ = [
    "AuditLog",
    "Branch",
    "Commit",
    "GitHubInstallation",
    "Issue",
    "Organization",
    "OrganizationMember",
    "PullRequest",
    "RefreshToken",
    "Repository",
    "RepositoryMembership",
    "RepositoryStatus",
    "Role",
    "Session",
    "User",
    "WebhookEvent",
]
