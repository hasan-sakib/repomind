from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, enum_column
from app.models.plan import Plan

if TYPE_CHECKING:
    from app.models.organization_member import OrganizationMember


class Organization(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False, index=True)
    # Billing/entitlement tier — see app/billing/plans.py for what each plan
    # allows and app/billing/entitlements.py for the one place that checks
    # it. Every organization starts on Free; nothing pays for anything
    # today (app/billing/provider.py is a Null implementation), so this is
    # set directly rather than through a real subscription.
    plan: Mapped[Plan] = mapped_column(
        enum_column(Plan, "organization_plan"), nullable=False, default=Plan.FREE
    )

    members: Mapped[list["OrganizationMember"]] = relationship(
        back_populates="organization", cascade="all, delete-orphan"
    )
