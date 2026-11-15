"""
User database queries.

TRANSACTION RULE for the auth/user/admin modules: repositories only add /
flush / query. They NEVER commit. The service commits once at the end of a
use case, so multi-step operations (e.g. change password + revoke all
sessions) succeed or fail as ONE unit.
"""

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.modules.user.model import User
from app.modules.user.roles import UserRole


def get_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    # Callers pass an already-normalised (lower-cased) email.
    return db.scalar(select(User).where(User.email == email))


def email_exists(db: Session, email: str) -> bool:
    return db.scalar(select(func.count()).select_from(User).where(User.email == email)) > 0


def create(
    db: Session,
    *,
    name: str,
    email: str,
    password_hash: str,
    role: UserRole,
    is_active: bool = True,
) -> User:
    user = User(
        name=name,
        email=email,
        password_hash=password_hash,
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.flush()  # sends INSERT now so DB constraints are checked; no commit
    return user


def list_users(
    db: Session,
    *,
    roles: list[UserRole],
    search: str | None = None,
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[User], int]:
    statement = select(User).where(User.role.in_(roles))

    if search and search.strip():
        # Escape LIKE wildcards so a search for "%" doesn't match everything.
        term = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{term}%"
        statement = statement.where(
            or_(User.name.ilike(pattern, escape="\\"), User.email.ilike(pattern, escape="\\"))
        )

    if is_active is not None:
        statement = statement.where(User.is_active.is_(is_active))

    total = db.scalar(select(func.count()).select_from(statement.subquery()))

    statement = (
        statement.order_by(User.created_at.desc(), User.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(db.scalars(statement).all()), total


def lock_active_super_admin_ids(db: Session) -> list[uuid.UUID]:
    """
    Return ids of all ACTIVE super admins and LOCK those rows (FOR UPDATE)
    until the transaction ends.

    Why lock? Two Super Admins deactivating each other at the same moment
    would each see "2 active" and both succeed, leaving ZERO. With the lock,
    the second transaction waits, then sees the updated count.
    """
    # ORDER BY id: every transaction locks rows in the same order, which
    # prevents deadlocks between two concurrent admin operations.
    statement = (
        select(User.id)
        .where(User.role == UserRole.SUPER_ADMIN, User.is_active.is_(True))
        .order_by(User.id)
        .with_for_update()
    )
    return list(db.scalars(statement).all())


def super_admin_exists(db: Session) -> bool:
    statement = select(func.count()).select_from(User).where(User.role == UserRole.SUPER_ADMIN)
    return db.scalar(statement) > 0
