import hashlib
import hmac
import json

import httpx
import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock

from app.core.config import get_settings
from tests.integration.test_repository_connect import (
    _connect_installation,
    _mock_github_app_endpoints,
    _register_and_get_org_id,
)

pytestmark = pytest.mark.asyncio
settings = get_settings()


def _sign(body: bytes) -> str:
    digest = hmac.new(settings.github_webhook_secret.encode("utf-8"), body, hashlib.sha256)
    return f"sha256={digest.hexdigest()}"


async def _post_webhook(
    client: AsyncClient,
    *,
    event: str,
    delivery_id: str,
    payload: dict,
    sign: bool = True,
) -> httpx.Response:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "X-GitHub-Event": event,
        "X-GitHub-Delivery": delivery_id,
        "Content-Type": "application/json",
    }
    if sign:
        headers["X-Hub-Signature-256"] = _sign(body)
    return await client.post("/api/v1/webhooks/github", content=body, headers=headers)


async def _connect_repository(
    client: AsyncClient, httpx_mock: HTTPXMock, email: str
) -> tuple[str, str]:
    """Returns (organization_id, repository_id) for a freshly connected repo."""
    org_id = await _register_and_get_org_id(client, email)
    _mock_github_app_endpoints(httpx_mock)
    await _connect_installation(client, org_id)
    installations_response = await client.get(
        f"/api/v1/organizations/{org_id}/github/installations"
    )
    installations = installations_response.json()
    installation_id = installations[0]["id"]
    connect_response = await client.post(
        f"/api/v1/organizations/{org_id}/repositories",
        json={
            "installation_id": installation_id,
            "github_repo_id": 555,
            "full_name": "acme/widgets",
        },
    )
    return org_id, connect_response.json()["id"]


async def test_webhook_rejects_invalid_signature(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/webhooks/github",
        content=b'{"action": "opened"}',
        headers={
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "d1",
            "X-Hub-Signature-256": "sha256=deadbeef",
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "webhook_verification_failed"


async def test_webhook_rejects_missing_signature(client: AsyncClient) -> None:
    response = await _post_webhook(
        client, event="issues", delivery_id="d2", payload={"action": "opened"}, sign=False
    )
    assert response.status_code == 401


async def test_webhook_pull_request_creates_and_updates(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    _, repository_id = await _connect_repository(client, httpx_mock, "webhook-pr@example.com")

    pr_payload = {
        "action": "opened",
        "installation": {"id": 999},
        "repository": {"id": 555},
        "pull_request": {
            "number": 7,
            "title": "Add feature",
            "state": "open",
            "user": {"login": "ada"},
            "html_url": "https://github.com/acme/widgets/pull/7",
            "head": {"sha": "f" * 40},
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "closed_at": None,
            "merged_at": None,
        },
    }
    response = await _post_webhook(
        client, event="pull_request", delivery_id="pr-1", payload=pr_payload
    )
    assert response.status_code == 204

    prs = (await client.get(f"/api/v1/repositories/{repository_id}/pull-requests")).json()
    assert len(prs) == 1
    assert prs[0]["title"] == "Add feature"
    assert prs[0]["state"] == "open"

    # An update to the same PR (closed) upserts, not duplicates.
    pr_payload["action"] = "closed"
    pr_payload["pull_request"]["state"] = "closed"
    pr_payload["pull_request"]["closed_at"] = "2026-01-02T00:00:00Z"
    pr_payload["pull_request"]["updated_at"] = "2026-01-02T00:00:00Z"
    response = await _post_webhook(
        client, event="pull_request", delivery_id="pr-2", payload=pr_payload
    )
    assert response.status_code == 204

    prs = (await client.get(f"/api/v1/repositories/{repository_id}/pull-requests")).json()
    assert len(prs) == 1
    assert prs[0]["state"] == "closed"


async def test_webhook_duplicate_delivery_is_processed_once(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    _, repository_id = await _connect_repository(client, httpx_mock, "webhook-dup@example.com")

    issue_payload = {
        "action": "opened",
        "installation": {"id": 999},
        "repository": {"id": 555},
        "issue": {
            "number": 3,
            "title": "Bug report",
            "state": "open",
            "user": {"login": "grace"},
            "html_url": "https://github.com/acme/widgets/issues/3",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
            "closed_at": None,
        },
    }

    first = await _post_webhook(
        client, event="issues", delivery_id="same-delivery-id", payload=issue_payload
    )
    assert first.status_code == 204
    second = await _post_webhook(
        client, event="issues", delivery_id="same-delivery-id", payload=issue_payload
    )
    assert second.status_code == 204

    issues = (await client.get(f"/api/v1/repositories/{repository_id}/issues")).json()
    assert len(issues) == 1


async def test_webhook_push_to_default_branch_triggers_resync(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    _, repository_id = await _connect_repository(client, httpx_mock, "webhook-push@example.com")
    before = (await client.get(f"/api/v1/repositories/{repository_id}")).json()
    first_synced_at = before["repository"]["last_synced_at"]
    assert first_synced_at is not None

    push_payload = {
        "ref": "refs/heads/main",
        "installation": {"id": 999},
        "repository": {"id": 555},
    }
    response = await _post_webhook(client, event="push", delivery_id="push-1", payload=push_payload)
    assert response.status_code == 204

    after = (await client.get(f"/api/v1/repositories/{repository_id}")).json()
    assert after["repository"]["status"] == "ready"
    assert after["repository"]["last_synced_at"] >= first_synced_at


async def test_webhook_push_to_non_default_branch_does_not_trigger_resync(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    _, repository_id = await _connect_repository(
        client, httpx_mock, "webhook-push-feature@example.com"
    )
    before = (await client.get(f"/api/v1/repositories/{repository_id}")).json()

    push_payload = {
        "ref": "refs/heads/some-feature-branch",
        "installation": {"id": 999},
        "repository": {"id": 555},
    }
    response = await _post_webhook(
        client, event="push", delivery_id="push-feature-1", payload=push_payload
    )
    assert response.status_code == 204

    after = (await client.get(f"/api/v1/repositories/{repository_id}")).json()
    assert after["repository"]["last_synced_at"] == before["repository"]["last_synced_at"]


async def test_webhook_installation_deleted_cascades_repositories(
    client: AsyncClient, httpx_mock: HTTPXMock
) -> None:
    org_id, repository_id = await _connect_repository(
        client, httpx_mock, "webhook-uninstall@example.com"
    )

    response = await _post_webhook(
        client,
        event="installation",
        delivery_id="install-deleted-1",
        payload={"action": "deleted", "installation": {"id": 999}},
    )
    assert response.status_code == 204

    repos = (await client.get(f"/api/v1/organizations/{org_id}/repositories")).json()
    assert repos == []

    overview = await client.get(f"/api/v1/repositories/{repository_id}")
    assert overview.status_code == 404
