import re
import secrets

_SLUG_INVALID_CHARS = re.compile(r"[^a-z0-9]+")


def slugify(value: str) -> str:
    slug = _SLUG_INVALID_CHARS.sub("-", value.lower()).strip("-")
    return slug or "org"


def slugify_with_suffix(value: str) -> str:
    """A slug with a short random suffix, for cases where base uniqueness
    isn't checked against the database (e.g. generating a first candidate
    before the uniqueness-retry loop in organization_service)."""
    return f"{slugify(value)}-{secrets.token_hex(3)}"
