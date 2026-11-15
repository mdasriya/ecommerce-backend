"""
Refresh-token (session) persistence. Never commits; the service does.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.modules.auth.model import RefreshToken


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create(
    db: Session,
    *,
    user_id: uuid.UUID,
    family_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
) -> RefreshToken:
    token = RefreshToken(
        user_id=user_id,
        family_id=family_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(token)
    db.flush()
    return token


def get_by_hash_for_update(db: Session, token_hash: str) -> RefreshToken | None:
    """
    FOR UPDATE: if the same refresh token is sent twice at the same moment,
    the second request waits for the first to finish and then sees it as
    already revoked, so a token can never be rotated twice.
    """
    statement = (
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .with_for_update()
    )
    return db.scalar(statement)


def family_has_active_token(db: Session, family_id: uuid.UUID) -> bool:
    """True if the session (family) still has a usable, unexpired token."""
    statement = (
        select(RefreshToken.id)
        .where(
            RefreshToken.family_id == family_id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > _now(),
        )
        .limit(1)
    )
    return db.scalar(statement) is not None


def revoke(db: Session, token: RefreshToken) -> None:
    if token.revoked_at is None:
        token.revoked_at = _now()


def revoke_family(db: Session, family_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


def revoke_all_for_user(db: Session, user_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


def delete_expired(db: Session, older_than: datetime) -> int:
    """Housekeeping: remove tokens that expired before `older_than`."""
    result = db.execute(delete(RefreshToken).where(RefreshToken.expires_at < older_than))
    return result.rowcount or 0
