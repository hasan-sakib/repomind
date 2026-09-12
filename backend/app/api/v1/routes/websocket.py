"""The single subscriber side of the unified real-time event system (see
docs/architecture/0010-realtime-infrastructure.md): one WebSocket per
connected organization, forwarding whatever app/events/bus.py publishes
on that organization's channel. Auth mirrors
app/api/deps.py::get_current_user_and_session + require_role(VIEWER), but
a WebSocket dependency can't raise HTTPException the way an HTTP one
does, so it's inlined as a plain function returning bool and the route
closes the connection itself on failure.
"""

import asyncio
import contextlib
import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.security.tokens import InvalidTokenError, decode_access_token
from app.db.session import async_session_factory
from app.events.bus import subscribe
from app.models.role import Role
from app.repositories import session_repository
from app.services import organization_service
from app.services.exceptions import AppError

router = APIRouter(tags=["realtime"])
logger = logging.getLogger("repomind.websocket")

# Detects a half-open connection (network drop with no clean close, e.g.
# a laptop sleeping) — a dead socket's send() eventually fails, which
# tears down the connection's tasks instead of leaking them forever.
_HEARTBEAT_SECONDS = 25


async def _authenticated_member(rm_session: str | None, organization_id: uuid.UUID) -> bool:
    if rm_session is None:
        return False
    try:
        payload = decode_access_token(rm_session)
    except InvalidTokenError:
        return False

    async with async_session_factory() as db:
        session_row = await session_repository.get_by_id(db, payload.session_id)
        now = datetime.now(UTC)
        if (
            session_row is None
            or session_row.revoked_at is not None
            or session_row.expires_at < now
            or session_row.user_id != payload.user_id
        ):
            return False
        try:
            await organization_service.require_role(
                db, organization_id=organization_id, user_id=payload.user_id, minimum=Role.VIEWER
            )
        except AppError:
            return False
    return True


def _origin_allowed(websocket: WebSocket) -> bool:
    """Defense in depth against cross-site WebSocket hijacking. The
    primary defense is the same one app/api/deps.py::require_csrf_header
    relies on for mutating HTTP requests: the session cookie is
    SameSite=Lax, so a cross-*site* page's script-initiated WebSocket
    handshake never carries it in the first place — this only tightens
    things further for cross-*origin*-but-same-site cases."""
    origin = websocket.headers.get("origin")
    if origin is None:
        return True
    return origin in get_settings().cors_origins


@router.websocket("/ws/organizations/{organization_id}")
async def organization_events(
    websocket: WebSocket,
    organization_id: uuid.UUID,
    rm_session: Annotated[str | None, Cookie()] = None,
) -> None:
    if not _origin_allowed(websocket) or not await _authenticated_member(
        rm_session, organization_id
    ):
        await websocket.close(code=4401)
        return

    await websocket.accept()
    logger.info("WebSocket connected: organization=%s", organization_id)

    forward_task = asyncio.create_task(_forward_events(websocket, organization_id))
    heartbeat_task = asyncio.create_task(_heartbeat(websocket))
    receive_task = asyncio.create_task(_drain_client_messages(websocket))
    pending: set[asyncio.Task[object]] = {forward_task, heartbeat_task, receive_task}

    try:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            if task.cancelled():
                continue
            exc = task.exception()
            if exc is not None:
                raise exc
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 — never let one connection's error crash the server
        logger.exception("WebSocket error: organization=%s", organization_id)
    finally:
        for task in pending:
            task.cancel()
        for task in pending:
            with contextlib.suppress(Exception):
                await task
        logger.info("WebSocket disconnected: organization=%s", organization_id)


async def _forward_events(websocket: WebSocket, organization_id: uuid.UUID) -> None:
    async for event in subscribe(organization_id):
        await websocket.send_text(event.model_dump_json())


async def _drain_client_messages(websocket: WebSocket) -> None:
    """We don't expect the client to send anything meaningful — this loop
    exists purely to detect a disconnect promptly (via the
    WebSocketDisconnect that `receive_text()` raises) rather than only
    noticing when a send fails. Any actual message content is discarded;
    a single non-disconnect message must NOT end the connection, which is
    why this loops instead of awaiting just one `receive_text()` call."""
    while True:
        await websocket.receive_text()


async def _heartbeat(websocket: WebSocket) -> None:
    while True:
        await asyncio.sleep(_HEARTBEAT_SECONDS)
        await websocket.send_json({"category": "ping", "at": datetime.now(UTC).isoformat()})
