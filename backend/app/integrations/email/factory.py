from functools import lru_cache

from app.core.config import get_settings
from app.integrations.email.console_sender import ConsoleEmailSender
from app.integrations.email.sender import EmailSender

settings = get_settings()


@lru_cache
def get_email_sender() -> EmailSender:
    if settings.environment == "production":
        # ConsoleEmailSender logs the raw password-reset / email-verification
        # link — including its bearer token — to stdout. That's a deliberate,
        # acceptable tradeoff for local development (see ConsoleEmailSender's
        # docstring) but never acceptable in production: fail loudly here
        # rather than silently leak reset tokens into production logs.
        # Implement a real EmailSender and wire it in here before deploying.
        raise RuntimeError(
            "No production EmailSender is configured — ConsoleEmailSender must "
            "never be used in production (see docs/architecture/security.md)."
        )
    return ConsoleEmailSender()
