import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from app.core.config import settings

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=2)

# Pre-computed dummy hash for constant-time login response when an email does not exist.
_DUMMY_PASSWORD_HASH = password_hasher.hash("dummy-timing-equalization-password-never-used")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        return password_hasher.verify(encoded_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False


def dummy_verify_password(password: str) -> None:
    """Run Argon2id verification on a dummy hash to reduce email-enumeration timing leaks."""
    verify_password(password, _DUMMY_PASSWORD_HASH)


def create_access_token(user_id: UUID) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_ttl_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> UUID:
    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"require": ["sub", "exp", "iat"]},
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Wrong token type")
    return UUID(payload["sub"])


def generate_refresh_token() -> tuple[str, str, datetime]:
    """Return (raw_token, sha256_hex_hash, expires_at)."""
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)
    return raw, token_hash, expires_at


def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)
