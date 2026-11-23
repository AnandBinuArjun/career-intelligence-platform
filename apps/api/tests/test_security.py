from uuid import uuid4

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_verifies_and_is_not_plaintext():
    raw = "a-long-example-password-123"
    encoded = hash_password(raw)
    assert encoded != raw
    assert verify_password(raw, encoded)
    assert not verify_password("wrong-password", encoded)


def test_access_token_round_trip():
    user_id = uuid4()
    token = create_access_token(user_id)
    assert decode_access_token(token) == user_id
