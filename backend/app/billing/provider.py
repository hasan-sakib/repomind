"""Abstraction over a subscription-billing provider (Stripe, Paddle, ...).

No concrete provider is wired up yet — see NullBillingProvider below and
docs/architecture/0011-saas-management.md for why that's a deliberate,
documented scope decision rather than an oversight. Callers (app/api/v1/
routes/organizations.py) depend only on this interface, exactly the same
shape as AIProvider/EmbeddingProvider (app/ai/), so a real provider can be
implemented and swapped in later via app/billing/factory.py without
touching route or service code.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.organization import Organization
from app.models.plan import Plan
from app.services.exceptions import BillingNotConfiguredError


@dataclass(frozen=True, slots=True)
class CheckoutSession:
    url: str


class BillingProvider(ABC):
    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Whether a real billing backend is wired up. The frontend uses
        this to decide between showing a real checkout flow and the
        interim "change plan directly" control
        (organization_service.set_plan) that's available while it's
        false."""
        ...

    @abstractmethod
    async def create_checkout_session(
        self, *, organization: Organization, plan: Plan
    ) -> CheckoutSession:
        """Start a hosted checkout flow for upgrading `organization` to
        `plan`. Must not mutate `organization.plan` itself — that only
        happens once the provider confirms payment (e.g. a webhook)."""
        ...

    @abstractmethod
    async def create_billing_portal_session(self, *, organization: Organization) -> str:
        """A URL to the provider's self-serve billing portal (update card,
        view invoices, cancel) for an already-paying organization."""
        ...


class NullBillingProvider(BillingProvider):
    """The default, and only, provider until a real one is configured. Every
    method raises — there is nothing to redirect to — which is exactly why
    `is_configured` exists: callers check it first and fall back to the
    manual plan-change endpoint instead of ever calling these."""

    @property
    def is_configured(self) -> bool:
        return False

    async def create_checkout_session(
        self, *, organization: Organization, plan: Plan
    ) -> CheckoutSession:
        raise BillingNotConfiguredError("No billing provider is configured")

    async def create_billing_portal_session(self, *, organization: Organization) -> str:
        raise BillingNotConfiguredError("No billing provider is configured")
