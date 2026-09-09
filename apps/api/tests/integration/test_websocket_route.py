"""Tests the WebSocket route itself (app/api/v1/routes/websocket.py) —
auth rejection, message delivery once connected, and per-organization
scoping. Uses Starlette's synchronous TestClient (the only client that
supports `websocket_connect`) alongside the ordinary async `client`
fixture for HTTP setup (register/login/create org) — both operate on the
same underlying `app`, so state committed via one is visible to the
other. Requires a real Redis connection (the same one the FastAPI app's
arq pool already requires at startup).
"""

import asyncio
import contextlib
import uuid
from collections.abc import Iterator
from concurrent.futures import CancelledError as FutureCancelledError

import pytest
from httpx import AsyncClient
from starlette.testclient import TestClient, WebSocketTestSession
from starlette.websockets import WebSocketDisconnect

from app.events.publish import publish_notification
from app.main import app

pytestmark = pytest.mark.asyncio


@contextlib.contextmanager
def _connect(tc: TestClient, url: str, **kwargs: object) -> Iterator[WebSocketTestSession]:
    """Wraps `TestClient.websocket_connect` to swallow a known Starlette
    TestClient teardown flake: tearing down a WebSocketTestSession's
    portal-backed task occasionally raises `concurrent.futures.
    CancelledError` from its own internal `future.result()` cleanup call,
    with no exception ever having occurred in the `with` body — i.e. the
    connection and every assertion inside it already succeeded by the
    time this fires. It's test-client cleanup noise, not an app bug."""
    session = tc.websocket_connect(url, **kwargs)
    ws = session.__enter__()
    try:
        yield ws
    finally:
        with contextlib.suppress(FutureCancelledError):
            session.__exit__(None, None, None)


async def _register_and_get_session(client: AsyncClient, email: str) -> tuple[str, str]:
    """Returns (organization_id, rm_session cookie value)."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-battery", "full_name": "Test User"},
    )
    assert response.status_code == 201, response.text
    me = await client.get("/api/v1/auth/me")
    organization_id = str(me.json()["organizations"][0]["organization"]["id"])
    session_token = client.cookies["rm_session"]
    return organization_id, session_token


async def test_connection_without_a_session_cookie_is_rejected(client: AsyncClient) -> None:
    organization_id, _ = await _register_and_get_session(client, "ws-noauth@example.com")

    with (
        TestClient(app) as tc,
        pytest.raises(WebSocketDisconnect) as exc_info,
        _connect(tc, f"/api/v1/ws/organizations/{organization_id}"),
    ):
        pass
    assert exc_info.value.code == 4401


async def test_connection_for_an_organization_the_user_does_not_belong_to_is_rejected(
    client: AsyncClient,
) -> None:
    _, session_token = await _register_and_get_session(client, "ws-wrongorg@example.com")
    someone_elses_org = uuid.uuid4()

    with TestClient(app) as tc:
        with (
            pytest.raises(WebSocketDisconnect) as exc_info,
            _connect(
                tc,
                f"/api/v1/ws/organizations/{someone_elses_org}",
                cookies={"rm_session": session_token},
            ),
        ):
            pass
        assert exc_info.value.code == 4401


async def test_authenticated_member_connects_and_receives_a_published_event(
    client: AsyncClient,
) -> None:
    organization_id, session_token = await _register_and_get_session(
        client, "ws-member@example.com"
    )

    with (
        TestClient(app) as tc,
        _connect(
            tc,
            f"/api/v1/ws/organizations/{organization_id}",
            cookies={"rm_session": session_token},
        ) as ws,
    ):
        # Give the server's forward_task a moment to actually
        # subscribe to Redis — publishing before that lands would
        # otherwise just be lost (pub/sub never queues for late
        # subscribers), same race as in test_events_bus.py.
        await asyncio.sleep(0.3)
        await publish_notification(
            organization_id=uuid.UUID(organization_id),
            title="Hello over the wire",
            level="info",
        )
        message = ws.receive_json()

    assert message["category"] == "notification"
    assert message["title"] == "Hello over the wire"
    assert message["organization_id"] == organization_id


async def test_disconnecting_does_not_crash_the_server(client: AsyncClient) -> None:
    """A best-effort smoke test for the cleanup path: closing one
    connection (the `with` block's __exit__ sends a close frame) must not
    raise or leave the server in a bad state — a second connection on the
    very same organization, opened right after, still works."""
    organization_id, session_token = await _register_and_get_session(
        client, "ws-disconnect@example.com"
    )

    # Two separate TestClient instances (each its own portal/event loop)
    # rather than reusing one — this is the closest analogue to two real,
    # independent browser connections, and sidesteps a Starlette-internal
    # race when a second websocket_connect() reuses a portal right after
    # a prior one on it just closed.
    with (
        TestClient(app) as tc,
        _connect(
            tc,
            f"/api/v1/ws/organizations/{organization_id}",
            cookies={"rm_session": session_token},
        ) as ws,
    ):
        await asyncio.sleep(0.3)
        await publish_notification(
            organization_id=uuid.UUID(organization_id), title="First", level="info"
        )
        first_message = ws.receive_json()

    with (
        TestClient(app) as tc,
        _connect(
            tc,
            f"/api/v1/ws/organizations/{organization_id}",
            cookies={"rm_session": session_token},
        ) as ws,
    ):
        await asyncio.sleep(0.3)
        await publish_notification(
            organization_id=uuid.UUID(organization_id), title="Still alive", level="info"
        )
        message = ws.receive_json()

    assert first_message["title"] == "First"
    assert message["title"] == "Still alive"
