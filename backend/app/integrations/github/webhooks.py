import hashlib
import hmac

from app.core.config import get_settings

settings = get_settings()

SUPPORTED_EVENTS = {"push", "pull_request", "issues", "installation", "installation_repositories"}


def verify_signature(payload: bytes, signature_header: str | None) -> bool:
    """Verifies the `X-Hub-Signature-256` header GitHub sends on every
    webhook delivery. Never process a webhook payload without calling this
    first — the payload is otherwise attacker-controlled input with no
    other authentication.

    Fails closed if `GITHUB_WEBHOOK_SECRET` isn't configured: an empty
    secret would otherwise mean HMAC-ing with a known (empty) key, which
    anyone can reproduce without knowing anything — that's equivalent to
    no verification at all, not a fail-safe default."""
    if not settings.github_webhook_secret:
        return False
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        settings.github_webhook_secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)
