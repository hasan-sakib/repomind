import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.security.tokens import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_opaque_token,
)

settings = get_settings()


def test_access_token_roundtrip() -> None:
    user_id = uuid.uuid4()
    session_id = uuid.uuid4()
    token = create_access_token(user_id, session_id)
    payload = decode_access_token(token)
    assert payload.user_id == user_id
    assert payload.session_id == session_id


def test_decode_rejects_expired_token() -> None:
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "sid": str(uuid.uuid4()),
            "type": "access",
            "iat": now - timedelta(minutes=30),
            "exp": now - timedelta(minutes=15),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(InvalidTokenError):
        decode_access_token(expired)


def test_decode_rejects_wrong_signature() -> None:
    token = create_access_token(uuid.uuid4(), uuid.uuid4())
    tampered = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(InvalidTokenError):
        decode_access_token(tampered)


def test_decode_rejects_wrong_token_type() -> None:
    now = datetime.now(UTC)
    other_type_token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "sid": str(uuid.uuid4()),
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(minutes=15),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(InvalidTokenError):
        decode_access_token(other_type_token)


def test_hash_opaque_token_is_deterministic_and_one_way() -> None:
    assert hash_opaque_token("abc") == hash_opaque_token("abc")
    assert hash_opaque_token("abc") != "abc"
    assert hash_opaque_token("abc") != hash_opaque_token("abd")
