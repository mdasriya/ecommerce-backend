"""
Authentication business logic.

Every public function here is ONE use case and ends with exactly one
db.commit(), so each use case is all-or-nothing.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.core.exceptions import AppException
from app.modules.auth import repository as token_repository
from app.modules.auth.model import RefreshToken
from app.modules.user import repository as user_repository
from app.modules.user.model import User
from app.modules.user.roles import UserRole

INVALID_CREDENTIALS = "Invalid email or password"
INVALID_REFRESH_TOKEN = "Invalid or expired refresh token"
ACCOUNT_DEACTIVATED = "Account is deactivated"


@dataclass(frozen=True)
class IssuedTokens:
    access_token: str
    refresh_token: str
    expires_in: int


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _unauthorized(message: str) -> AppException:
    return AppException(message=message, status_code=401, headers={"WWW-Authenticate": "Bearer"})


def _issue_tokens(db: Session, user: User, family_id: uuid.UUID | None = None) -> IssuedTokens:
    """
    Create an access token + a NEW refresh token row.
    family_id=None -> a new login session; otherwise continue a rotation chain.
    Only the SHA-256 hash of the refresh token is stored.
    """
    access_token, expires_in = security.create_access_token(user.id)
    raw_refresh = security.generate_refresh_token()

    token_repository.create(
        db,
        user_id=user.id,
        family_id=family_id or uuid.uuid4(),
        token_hash=security.hash_refresh_token(raw_refresh),
        expires_at=security.refresh_token_expiry(),
    )
    return IssuedTokens(access_token=access_token, refresh_token=raw_refresh, expires_in=expires_in)


def create_user_account(
    db: Session, *, name: str, email: str, password: str, role: UserRole
) -> User:
    """
    Shared by public registration, admin creation and the bootstrap CLI.
    Does NOT commit (callers decide). Duplicate emails -> 409.
    """
    if user_repository.email_exists(db, email):
        raise AppException(message="An account with this email already exists", status_code=409)

    return user_repository.create(
        db,
        name=name,
        email=email,
        password_hash=security.hash_password(password),
        role=role,
    )


def commit_or_conflict(db: Session) -> None:
    """
    The email check above can race: two simultaneous registrations with the
    same email both pass it. The UNIQUE index then rejects the second INSERT;
    we turn that database error into a clean 409 instead of a 500.
    """
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppException(message="An account with this email already exists", status_code=409) from exc


# ------------------------------------------------------------------ use cases
def register(db: Session, *, name: str, email: str, password: str) -> User:
    # Role is hard-coded: public registration can ONLY ever create a USER.
    user = create_user_account(db, name=name, email=email, password=password, role=UserRole.USER)
    commit_or_conflict(db)
    db.refresh(user)
    return user


def login(db: Session, *, email: str, password: str) -> tuple[User, IssuedTokens]:
    user = user_repository.get_by_email(db, email)

    if user is None:
        security.burn_password_check_time(password)  # equalise response time
        raise _unauthorized(INVALID_CREDENTIALS)

    if not security.verify_password(password, user.password_hash):
        raise _unauthorized(INVALID_CREDENTIALS)

    # Checked AFTER the password, so this message is only revealed to someone
    # who already knows the correct password.
    if not user.is_active:
        raise AppException(message=ACCOUNT_DEACTIVATED, status_code=403)

    # Transparently upgrade old hashes if we ever strengthen Argon2 settings.
    if security.password_needs_rehash(user.password_hash):
        user.password_hash = security.hash_password(password)

    tokens = _issue_tokens(db, user)
    db.commit()
    db.refresh(user)
    return user, tokens


def _is_concurrent_rotation(db: Session, stored: RefreshToken) -> bool:
    """
    A revoked token is NOT necessarily stolen. Two requests sent at the same
    moment with the same cookie (several tabs restored together, or a page
    load racing an API call) both reach the database: the first rotates the
    token, the second then finds it revoked a moment ago.

    Treat it as a race (not theft) only if BOTH hold:
      - it was revoked within REFRESH_TOKEN_REUSE_GRACE_SECONDS, and
      - its session still has an active token, i.e. it was revoked by a
        ROTATION. Logout / password change / reuse detection revoke the
        whole family, so they leave no active token and are never revived.
    """
    grace = settings.REFRESH_TOKEN_REUSE_GRACE_SECONDS
    if grace <= 0 or stored.revoked_at is None:
        return False
    if stored.revoked_at < _now() - timedelta(seconds=grace):
        return False
    return token_repository.family_has_active_token(db, stored.family_id)


def refresh(db: Session, *, raw_refresh_token: str) -> tuple[User, IssuedTokens]:
    """
    Refresh-token ROTATION with REUSE DETECTION:
      valid token   -> revoke it, issue a new one in the same family
      revoked token -> it was already used once, so someone has a copy:
                       revoke the WHOLE family (thief and victim both
                       must log in again) and reject.
                       Exception: a concurrent request within the short
                       grace window (see _is_concurrent_rotation).
    """
    stored = token_repository.get_by_hash_for_update(db, security.hash_refresh_token(raw_refresh_token))

    if stored is None:
        raise _unauthorized(INVALID_REFRESH_TOKEN)

    if stored.revoked_at is not None:
        if _is_concurrent_rotation(db, stored):
            user = user_repository.get_by_id(db, stored.user_id)
            if user is not None and user.is_active:
                tokens = _issue_tokens(db, user, family_id=stored.family_id)
                db.commit()
                db.refresh(user)
                return user, tokens
        token_repository.revoke_family(db, stored.family_id)
        db.commit()  # persist the revocation even though we reject the request
        raise _unauthorized(INVALID_REFRESH_TOKEN)

    if stored.expires_at <= _now():
        token_repository.revoke(db, stored)
        db.commit()
        raise _unauthorized(INVALID_REFRESH_TOKEN)

    user = user_repository.get_by_id(db, stored.user_id)
    if user is None or not user.is_active:
        token_repository.revoke_family(db, stored.family_id)
        db.commit()
        raise _unauthorized(INVALID_REFRESH_TOKEN)

    token_repository.revoke(db, stored)
    tokens = _issue_tokens(db, user, family_id=stored.family_id)
    db.commit()
    db.refresh(user)
    return user, tokens


def logout(db: Session, *, raw_refresh_token: str) -> None:
    """
    Revoke the session (whole token family) this refresh token belongs to.

    Idempotent and silent: unknown/already-revoked tokens also return success,
    so the endpoint can't be used to probe which tokens are valid, and a
    client retrying logout never gets a confusing error.
    """
    stored = token_repository.get_by_hash_for_update(db, security.hash_refresh_token(raw_refresh_token))
    if stored is not None:
        token_repository.revoke_family(db, stored.family_id)
        db.commit()


def update_me(db: Session, *, user: User, changes: dict) -> User:
    allowed = {"name"}  # explicit allow-list (see UpdateMeRequest)
    for field, value in changes.items():
        if field in allowed:
            setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def change_password(
    db: Session, *, user: User, current_password: str, new_password: str
) -> IssuedTokens:
    """
    Re-authenticates with the current password, sets the new one, logs out
    ALL sessions (all devices), then issues a fresh token pair so the device
    that made the change stays signed in.
    """
    if not security.verify_password(current_password, user.password_hash):
        # 400, not 401: a 401 would make most frontends think the SESSION
        # expired and log the user out.
        raise AppException(message="Current password is incorrect", status_code=400)

    user.password_hash = security.hash_password(new_password)
    token_repository.revoke_all_for_user(db, user.id)
    tokens = _issue_tokens(db, user)
    db.commit()
    return tokens
