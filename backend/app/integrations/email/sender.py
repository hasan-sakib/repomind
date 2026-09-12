from abc import ABC, abstractmethod


class EmailSender(ABC):
    """Abstraction over outbound transactional email. No real email
    provider (SES/Postmark/SendGrid) is configured yet — see
    ConsoleEmailSender and docs/architecture/backend-architecture.md for
    why that's a deliberate, documented gap rather than an oversight.
    Callers (auth_service) depend only on this interface so a real
    provider can be dropped in later without touching call sites."""

    @abstractmethod
    async def send(self, *, to: str, subject: str, body: str) -> None: ...
