import enum


class Role(enum.StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


# Highest to lowest privilege. Used by authorization checks to compare
# "does this member's role meet the minimum required role" without encoding
# the ordering in every call site.
_ROLE_RANK: dict[Role, int] = {
    Role.OWNER: 3,
    Role.ADMIN: 2,
    Role.DEVELOPER: 1,
    Role.VIEWER: 0,
}


def role_at_least(role: Role, minimum: Role) -> bool:
    return _ROLE_RANK[role] >= _ROLE_RANK[minimum]
