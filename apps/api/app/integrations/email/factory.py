from functools import lru_cache

from app.integrations.email.console_sender import ConsoleEmailSender
from app.integrations.email.sender import EmailSender


@lru_cache
def get_email_sender() -> EmailSender:
    return ConsoleEmailSender()
