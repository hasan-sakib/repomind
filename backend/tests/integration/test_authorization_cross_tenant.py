"""Explicit cross-tenant isolation tests: a user who is a legitimate
member of their own organization/repository must not be able to reach
another organization's conversations or indexing jobs by guessing/knowing
the other resource's id, even while presenting their own (valid)
repository_id in the URL.

app/api/deps.py's require_repository_access already stops the obvious
attack (using someone else's repository_id directly) — that's covered by
the `test_non_member_gets_404_on_*` tests scattered across the route test
files. What isn't covered anywhere else is the subtler case these tests
target: chat_service.get_conversation_or_raise and
indexing_service.get_job_or_raise fetch the nested resource by its own id
first and only *then* compare its repository_id — see
docs/architecture/security.md's "nested resource lookups" note. This file
proves that comparison actually fires."""

import uuid

import pytest
from httpx import AsyncClient
from pytest_httpx import HTTPXMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.indexing_job import IndexingJob
from app.models.indexing_status import IndexingJobStatus, IndexingTrigger
from app.repositories import indexing_job_repository
from tests.integration.test_repository_connect import (
    _connect_installation,
    _mock_github_app_endpoints,
    _register_and_get_org_id,
)

pytestmark = pytest.mark.asyncio


async def _connect_a_repository(
    client: AsyncClient, org_id: str, httpx_mock: HTTPXMock, *, installation_id: int = 999
) -> str:
    _mock_github_app_endpoints(httpx_mock)
    await _connect_installation(client, org_id, installation_id=installation_id)
    installations = (
        await client.get(f"/api/v1/organizations/{org_id}/github/installations")
    ).json()
    connect_response = await client.post(
        f"/api/v1/organizations/{org_id}/repositories",
        json={
            "installation_id": installations[0]["id"],
            "github_repo_id": 555,
            "full_name": "acme/widgets",
        },
    )
    assert connect_response.status_code == 201, connect_response.text
    return str(connect_response.json()["id"])


async def test_conversation_from_another_organizations_repository_is_not_reachable(
    client: AsyncClient,
    second_client: AsyncClient,
    httpx_mock: HTTPXMock,
) -> None:
    org_a = await _register_and_get_org_id(client, "org-a-owner@example.com")
    repo_a = await _connect_a_repository(client, org_a, httpx_mock)
    create_response = await client.post(f"/api/v1/repositories/{repo_a}/conversations")
    assert create_response.status_code == 201, create_response.text
    conversation_a_id = create_response.json()["id"]

    org_b = await _register_and_get_org_id(second_client, "org-b-owner@example.com")
    repo_b = await _connect_a_repository(second_client, org_b, httpx_mock, installation_id=1000)

    # org B's own member, authenticated, using org B's own (valid)
    # repository_id — but referencing org A's conversation id.
    response = await second_client.get(
        f"/api/v1/repositories/{repo_b}/conversations/{conversation_a_id}"
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "conversation_not_found"


async def test_conversation_messages_from_another_organization_cannot_receive_feedback(
    client: AsyncClient,
    second_client: AsyncClient,
    httpx_mock: HTTPXMock,
) -> None:
    org_a = await _register_and_get_org_id(client, "org-a-owner2@example.com")
    repo_a = await _connect_a_repository(client, org_a, httpx_mock)
    create_response = await client.post(f"/api/v1/repositories/{repo_a}/conversations")
    conversation_a_id = create_response.json()["id"]

    org_b = await _register_and_get_org_id(second_client, "org-b-owner2@example.com")
    repo_b = await _connect_a_repository(second_client, org_b, httpx_mock, installation_id=1000)

    response = await second_client.patch(
        f"/api/v1/repositories/{repo_b}/conversations/{conversation_a_id}"
        f"/messages/{uuid.uuid4()}/feedback",
        json={"feedback": "up"},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "conversation_not_found"


async def test_indexing_job_from_another_organizations_repository_is_not_reachable(
    client: AsyncClient,
    second_client: AsyncClient,
    httpx_mock: HTTPXMock,
    db_session: AsyncSession,
) -> None:
    org_a = await _register_and_get_org_id(client, "org-a-owner3@example.com")
    repo_a = await _connect_a_repository(client, org_a, httpx_mock)

    job: IndexingJob = indexing_job_repository.create(
        db_session,
        repository_id=uuid.UUID(repo_a),
        trigger=IndexingTrigger.MANUAL,
        commit_sha="a" * 40,
    )
    job.status = IndexingJobStatus.SUCCEEDED
    await db_session.commit()

    org_b = await _register_and_get_org_id(second_client, "org-b-owner3@example.com")
    repo_b = await _connect_a_repository(second_client, org_b, httpx_mock, installation_id=1000)

    response = await second_client.get(f"/api/v1/repositories/{repo_b}/indexing-jobs/{job.id}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "indexing_job_not_found"


async def test_listing_indexing_jobs_never_includes_another_organizations_jobs(
    client: AsyncClient,
    second_client: AsyncClient,
    httpx_mock: HTTPXMock,
    db_session: AsyncSession,
) -> None:
    org_a = await _register_and_get_org_id(client, "org-a-owner4@example.com")
    repo_a = await _connect_a_repository(client, org_a, httpx_mock)
    indexing_job_repository.create(
        db_session,
        repository_id=uuid.UUID(repo_a),
        trigger=IndexingTrigger.MANUAL,
        commit_sha="a" * 40,
    )
    await db_session.commit()

    org_b = await _register_and_get_org_id(second_client, "org-b-owner4@example.com")
    repo_b = await _connect_a_repository(second_client, org_b, httpx_mock, installation_id=1000)

    response = await second_client.get(f"/api/v1/repositories/{repo_b}/indexing-jobs")

    assert response.status_code == 200
    assert response.json() == []
