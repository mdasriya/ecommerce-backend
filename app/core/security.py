"""
Security primitives: password hashing, JWT access tokens, refresh tokens.

Contains NO database or HTTP code, so it is easy to test and review.
"""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import settings

# =========================================================== Passwords
# Argon2id with the library's defaults (RFC 9106 "low memory" profile:
# time_cost=3, memory_cost=64 MiB, parallelism=4). The salt is random per
# hash and stored inside the hash string itself, e.g.
#   $argon2id$v=19$m=65536,t=3,p=4$<salt>$<hash>
_password_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    return _password_hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Return True only if the password matches. Never raises for bad input."""
    try:
        return _password_hasher.verify(password_hash, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    """
    True if the hash was made with weaker/older parameters than the current
    ones. Lets us upgrade hashes transparently at the next successful login.
    """
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


@lru_cache
def _dummy_hash() -> str:
    return _password_hasher.hash(secrets.token_urlsafe(32))


def burn_password_check_time(plain_password: str) -> None:
    """
    Called at login when the email does NOT exist.

    Without this, "unknown email" responds in ~1 ms while "wrong password"
    takes ~50+ ms (Argon2 is intentionally slow). An attacker could measure
    that difference to discover which emails have accounts.
    """
    verify_password(plain_password, _dummy_hash())


# =========================================================== Access tokens (JWT)
ACCESS_TOKEN_TYPE = "access"


class TokenError(Exception):
    """Raised for any invalid/expired/malformed access token."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    """
    Create a signed, short-lived JWT.

    Returns (token, expires_in_seconds).

    Claims:
      sub  - user id (string). The ROLE IS NOT trusted from the token; it is
             loaded from the database on every request, so role changes and
             deactivations take effect immediately.
      type - "access"; prevents any other kind of token being used here.
      iat / exp - issued-at / expiry.
      iss  - issuer; rejects tokens minted by another system with the same key.
      jti  - unique token id (useful for logging/auditing).
    """
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    now = _now()
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
        "iss": settings.JWT_ISSUER,
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(
        payload,
        settings.JWT_SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )
    return token, expires_in


def decode_access_token(token: str) -> uuid.UUID:
    """
    Verify signature, expiry, issuer and token type. Return the user id.

    `algorithms=[...]` is an explicit allow-list: this blocks the classic
    "alg: none" and algorithm-confusion attacks.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
            issuer=settings.JWT_ISSUER,
            options={"require": ["exp", "iat", "sub", "iss", "type"]},
            leeway=10,  # tolerate 10 s of clock skew between servers
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid token") from exc

    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise TokenError("Invalid token type")

    try:
        return uuid.UUID(payload["sub"])
    except (ValueError, TypeError) as exc:
        raise TokenError("Invalid token subject") from exc


# =========================================================== Refresh tokens (opaque)
def generate_refresh_token() -> str:
    """
    64 random bytes (512 bits) from the OS CSPRNG, URL-safe encoded.
    Opaque: it carries no data; its meaning lives in the database.
    """
    return secrets.token_urlsafe(64)


def hash_refresh_token(token: str) -> str:
    """
    SHA-256 hex digest stored in the DB instead of the raw token.

    A fast hash is fine here (unlike passwords) because the input is 512 bits
    of randomness, so brute-forcing it is impossible. A fast, deterministic
    hash also lets us look the token up with a unique index.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return _now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
