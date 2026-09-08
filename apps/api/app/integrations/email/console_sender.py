import logging

from app.integrations.email.sender import EmailSender

logger = logging.getLogger("repomind.email")


class ConsoleEmailSender(EmailSender):
    """Logs the email instead of sending it. This is the only EmailSender
    implementation until a real transactional email provider is chosen —
    it exists so password-reset and email-verification flows are fully
    exercisable (and testable) without depending on external credentials.
    Swap for a real provider by implementing EmailSender and changing the
    wiring in app/integrations/email/factory.py."""

    async def send(self, *, to: str, subject: str, body: str) -> None:
        logger.info("EMAIL to=%s subject=%r\n%s", to, subject, body)
