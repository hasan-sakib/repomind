import jwt

from app.core.config import get_settings
from app.integrations.github.app_client import mint_app_jwt
from tests.conftest import TEST_RSA_PUBLIC_KEY_PEM

settings = get_settings()


def test_mint_app_jwt_is_verifiable_and_carries_app_id() -> None:
    token = mint_app_jwt()
    payload = jwt.decode(token, TEST_RSA_PUBLIC_KEY_PEM, algorithms=["RS256"])
    assert payload["iss"] == settings.github_app_id
    assert payload["exp"] > payload["iat"]


def test_mint_app_jwt_rejects_wrong_key() -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    other_public_pem = other_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    token = mint_app_jwt()
    try:
        jwt.decode(token, other_public_pem, algorithms=["RS256"])
        raise AssertionError("Expected signature verification to fail")
    except jwt.InvalidSignatureError:
        pass
