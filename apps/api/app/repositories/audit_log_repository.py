import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.audit_log import AuditLog


def create(
    db: AsyncSession,
    *,
    action: str,
    actor_user_id: uuid.UUID | None = None,
    organization_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    ip_address: str | None = None,
    extra: dict[str, object] | None = None,
) -> AuditLog:
    entry = AuditLog(
        action=action,
        actor_user_id=actor_user_id,
        organization_id=organization_id,
        target_type=target_type,
        target_id=target_id,
        ip_address=ip_address,
        extra=extra or {},
    )
    db.add(entry)
    return entry
