from functools import lru_cache

from app.billing.provider import BillingProvider, NullBillingProvider
from app.core.config import get_settings


@lru_cache
def get_billing_provider() -> BillingProvider:
    settings = get_settings()
    if settings.billing_provider == "null":
        return NullBillingProvider()
    raise ValueError(f"Unsupported billing provider: {settings.billing_provider}")
