import json
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Header, Request

from app.api.deps import DbSession
from app.integrations.github.webhooks import SUPPORTED_EVENTS, verify_signature
from app.services import sync_service, webhook_service
from app.services.exceptions import WebhookVerificationError

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github", status_code=204)
async def github_webhook(
    request: Request,
    db: DbSession,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Annotated[str | None, Header()] = None,
    x_github_event: Annotated[str | None, Header()] = None,
    x_github_delivery: Annotated[str | None, Header()] = None,
) -> None:
    raw_body = await request.body()

    # Never parse or act on a webhook payload before the signature is
    # verified against the raw bytes — this is attacker-controlled input
    # with no other authentication.
    if not verify_signature(raw_body, x_hub_signature_256):
        raise WebhookVerificationError("Invalid webhook signature")

    if not x_github_event or not x_github_delivery:
        raise WebhookVerificationError("Missing GitHub event headers")

    if x_github_event not in SUPPORTED_EVENTS:
        return  # Acknowledge, but there's nothing to do with it.

    payload = json.loads(raw_body)
    result = await webhook_service.process_webhook(
        db,
        github_delivery_id=x_github_delivery,
        event_type=x_github_event,
        payload=payload,
    )
    if result.resync_repository_id is not None:
        background_tasks.add_task(sync_service.run_sync_in_background, result.resync_repository_id)
