import json
from typing import Annotated

from fastapi import APIRouter, Header, Request

from app.api.deps import ArqPool, DbSession
from app.domain.indexing_status import IndexingTrigger
from app.integrations.github.webhooks import SUPPORTED_EVENTS, verify_signature
from app.repositories import repository_repository
from app.services import indexing_service, webhook_service
from app.services.exceptions import WebhookVerificationError

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/github", status_code=204)
async def github_webhook(
    request: Request,
    db: DbSession,
    arq_pool: ArqPool,
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
        await arq_pool.enqueue_job("sync_repository", str(result.resync_repository_id))
    if result.reindex is not None:
        repository_id, commit_sha = result.reindex
        repository = await repository_repository.get_by_id(db, repository_id)
        if repository is not None:
            # commit_sha always set here (the pushed commit), so this never
            # hits the "no synced default branch" guard in trigger_indexing.
            job, started = await indexing_service.trigger_indexing(
                db, repository=repository, trigger=IndexingTrigger.WEBHOOK, commit_sha=commit_sha
            )
            if started:
                await arq_pool.enqueue_job("index_repository", str(job.id))
