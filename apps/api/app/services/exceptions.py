"""Service-layer errors. Routes never construct HTTPException by hand for
these cases — a single exception handler (see app/main.py) converts any
AppError into the standard {"error": {"code", "message"}} envelope
documented in docs/api/api-design.md."""


class AppError(Exception):
    status_code: int = 400
    code: str = "error"

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class EmailAlreadyRegisteredError(AppError):
    status_code = 409
    code = "email_already_registered"


class InvalidCredentialsError(AppError):
    status_code = 401
    code = "invalid_credentials"


class NotAuthenticatedError(AppError):
    status_code = 401
    code = "not_authenticated"


class CsrfError(AppError):
    status_code = 403
    code = "csrf_failed"


class EmailNotVerifiedError(AppError):
    status_code = 403
    code = "email_not_verified"


class InvalidOrExpiredTokenError(AppError):
    status_code = 401
    code = "invalid_or_expired_token"


class GitHubAuthError(AppError):
    status_code = 502
    code = "github_auth_failed"


class OrganizationNotFoundError(AppError):
    status_code = 404
    code = "organization_not_found"


class InsufficientRoleError(AppError):
    status_code = 403
    code = "insufficient_role"


class LastOwnerError(AppError):
    status_code = 409
    code = "last_owner"


class UserNotFoundError(AppError):
    status_code = 404
    code = "user_not_found"


class MemberAlreadyExistsError(AppError):
    status_code = 409
    code = "member_already_exists"


class InstallationNotFoundError(AppError):
    status_code = 404
    code = "installation_not_found"


class RepositoryNotFoundError(AppError):
    status_code = 404
    code = "repository_not_found"


class RepositoryAlreadyConnectedError(AppError):
    status_code = 409
    code = "repository_already_connected"


class WebhookVerificationError(AppError):
    status_code = 401
    code = "webhook_verification_failed"


class RepositoryNotSyncedError(AppError):
    status_code = 409
    code = "repository_not_synced"


class IndexingJobNotFoundError(AppError):
    status_code = 404
    code = "indexing_job_not_found"


class ConversationNotFoundError(AppError):
    status_code = 404
    code = "conversation_not_found"


class MessageNotFoundError(AppError):
    status_code = 404
    code = "message_not_found"


class RegenerateNotAllowedError(AppError):
    status_code = 409
    code = "regenerate_not_allowed"


class ArchitectureFileNotFoundError(AppError):
    status_code = 404
    code = "architecture_file_not_found"


class ArchitecturePackageNotFoundError(AppError):
    status_code = 404
    code = "architecture_package_not_found"


class PullRequestNotFoundError(AppError):
    status_code = 404
    code = "pull_request_not_found"


class PullRequestAnalysisNotFoundError(AppError):
    status_code = 404
    code = "pull_request_analysis_not_found"
