from app.billing.plans import PLAN_LABELS, PLAN_LIMITS, limits_for
from app.models.plan import Plan


def test_every_plan_has_limits_and_a_label() -> None:
    for plan in Plan:
        assert plan in PLAN_LIMITS
        assert plan in PLAN_LABELS


def test_free_plan_caps_repositories_and_members() -> None:
    limits = limits_for(Plan.FREE)
    assert limits.max_repositories == 3
    assert limits.max_members == 3


def test_team_plan_is_unlimited() -> None:
    limits = limits_for(Plan.TEAM)
    assert limits.max_repositories is None
    assert limits.max_members is None


def test_pro_plan_is_between_free_and_team() -> None:
    free = limits_for(Plan.FREE)
    pro = limits_for(Plan.PRO)
    assert pro.max_repositories is not None
    assert pro.max_members is not None
    assert pro.max_repositories > free.max_repositories  # type: ignore[operator]
    assert pro.max_members > free.max_members  # type: ignore[operator]
