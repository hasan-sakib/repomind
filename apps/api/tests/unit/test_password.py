from app.core.security.password import hash_password, verify_password


def test_hash_and_verify_roundtrip() -> None:
    password_hash = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", password_hash)


def test_verify_rejects_wrong_password() -> None:
    password_hash = hash_password("correct-horse-battery-staple")
    assert not verify_password("wrong-password", password_hash)


def test_verify_rejects_malformed_hash() -> None:
    assert not verify_password("anything", "not-a-real-argon2-hash")


def test_hash_is_salted_and_nondeterministic() -> None:
    hash_one = hash_password("same-password")
    hash_two = hash_password("same-password")
    assert hash_one != hash_two
    assert verify_password("same-password", hash_one)
    assert verify_password("same-password", hash_two)
