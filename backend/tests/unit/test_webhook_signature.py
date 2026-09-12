import hashlib
import hmac

import pytest

from app.core.config import get_settings
from app.integrations.github.webhooks import verify_signature

settings = get_settings()


def _sign(payload: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_valid_signature_is_accepted() -> None:
    payload = b'{"action": "opened"}'
    signature = _sign(payload, settings.github_webhook_secret)
    assert verify_signature(payload, signature) is True


def test_wrong_secret_is_rejected() -> None:
    payload = b'{"action": "opened"}'
    signature = _sign(payload, "not-the-real-secret")
    assert verify_signature(payload, signature) is False


def test_tampered_payload_is_rejected() -> None:
    payload = b'{"action": "opened"}'
    signature = _sign(payload, settings.github_webhook_secret)
    tampered_payload = b'{"action": "closed"}'
    assert verify_signature(tampered_payload, signature) is False


def test_missing_signature_header_is_rejected() -> None:
    assert verify_signature(b"{}", None) is False


def test_malformed_signature_header_is_rejected() -> None:
    assert verify_signature(b"{}", "not-sha256-prefixed") is False


def test_empty_configured_secret_rejects_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    """An unset GITHUB_WEBHOOK_SECRET must fail closed — HMAC-ing with a
    known (empty) key is something anyone can reproduce, so this must not
    silently behave as "no verification" while looking verified."""
    import app.integrations.github.webhooks as webhooks_module

    monkeypatch.setattr(webhooks_module.settings, "github_webhook_secret", "")
    payload = b'{"action": "opened"}'
    # Even a signature computed with the empty key (which anyone can do
    # without knowing any secret) must not be accepted.
    forged = _sign(payload, "")
    assert verify_signature(payload, forged) is False
