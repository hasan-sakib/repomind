from app.models.role import Role, role_at_least


def test_owner_meets_every_minimum() -> None:
    for minimum in Role:
        assert role_at_least(Role.OWNER, minimum)


def test_viewer_only_meets_viewer_minimum() -> None:
    assert role_at_least(Role.VIEWER, Role.VIEWER)
    assert not role_at_least(Role.VIEWER, Role.DEVELOPER)
    assert not role_at_least(Role.VIEWER, Role.ADMIN)
    assert not role_at_least(Role.VIEWER, Role.OWNER)


def test_ordering_is_owner_admin_developer_viewer() -> None:
    assert role_at_least(Role.ADMIN, Role.DEVELOPER)
    assert role_at_least(Role.ADMIN, Role.VIEWER)
    assert not role_at_least(Role.ADMIN, Role.OWNER)
    assert role_at_least(Role.DEVELOPER, Role.VIEWER)
    assert not role_at_least(Role.DEVELOPER, Role.ADMIN)
