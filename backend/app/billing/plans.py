"""The one place plan limits are defined. Every entitlement check in
app/billing/entitlements.py reads from PLAN_LIMITS — nothing else in the
codebase should hardcode a number like "3 repositories" or compare
`organization.plan` directly. See
docs/architecture/0011-saas-management.md."""

from dataclasses import dataclass

from app.models.plan import Plan

# None means unlimited.
UNLIMITED = None


@dataclass(frozen=True)
class PlanLimits:
    max_repositories: int | None
    max_members: int | None


PLAN_LIMITS: dict[Plan, PlanLimits] = {
    Plan.FREE: PlanLimits(max_repositories=3, max_members=3),
    Plan.PRO: PlanLimits(max_repositories=25, max_members=20),
    Plan.TEAM: PlanLimits(max_repositories=UNLIMITED, max_members=UNLIMITED),
}

PLAN_LABELS: dict[Plan, str] = {
    Plan.FREE: "Free",
    Plan.PRO: "Pro",
    Plan.TEAM: "Team",
}


def limits_for(plan: Plan) -> PlanLimits:
    return PLAN_LIMITS[plan]
