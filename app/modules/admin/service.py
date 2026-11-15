"""
Admin / customer management business rules.

Privilege rules enforced here (in addition to the route-level role checks):
  * Nobody can change their OWN role or their OWN active status.
  * Only roles allowed by roles.ASSIGNABLE_ROLES can be assigned
    (today: only SUPER_ADMIN assigns roles).
  * The last ACTIVE Super Admin can never be deactivated or demoted.
  * Customer endpoints only ever touch role=USER accounts, so an ADMIN can't
    use them to deactivate another admin or a Super Admin.
"""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import AppException
from app.modules.auth import repository as token_repository
from app.modules.auth import service as auth_service
from app.modules.user import repository as user_repository
from app.modules.user.model import User
from app.modules.user.roles import STAFF_ROLES, UserRole, can_assign_role


# ----------------------------------------------------------------- helpers
def _not_found(kind: str) -> AppException:
    return AppException(message=f"{kind} not found", status_code=404)


def _get_user_with_role(db: Session, user_id: uuid.UUID, roles: frozenset[UserRole], kind: str) -> User:
    user = user_repository.get_by_id(db, user_id)
    # Wrong role -> 404 (not 403): don't reveal that the id exists elsewhere.
    if user is None or user.role not in roles:
        raise _not_found(kind)
    return user


def _ensure_not_self(actor: User, target: User, action: str) -> None:
    if actor.id == target.id:
        raise AppException(message=f"You cannot change your own {action}", status_code=403)


def _lock_and_ensure_super_admin_remains(db: Session, target: User) -> None:
    """
    Call BEFORE deactivating/demoting `target`.
    Locks all active Super Admin rows first (consistent order), THEN re-reads
    the target, so the check sees committed, up-to-date data.
    """
    active_ids = user_repository.lock_active_super_admin_ids(db)
    db.refresh(target)
    if target.id in active_ids and len(active_ids) <= 1:
        raise AppException(
            message="Cannot deactivate or demote the last active Super Admin",
            status_code=409,
        )


def _set_active(db: Session, target: User, is_active: bool) -> User:
    target.is_active = is_active
    if not is_active:
        # Kill all their sessions immediately. (Access tokens are also
        # rejected on the next request because is_active is checked from the DB.)
        token_repository.revoke_all_for_user(db, target.id)
    db.commit()
    db.refresh(target)
    return target


# ======================================================= Staff (Super Admin)
def create_admin(db: Session, *, name: str, email: str, password: str) -> User:
    user = auth_service.create_user_account(
        db, name=name, email=email, password=password, role=UserRole.ADMIN
    )
    auth_service.commit_or_conflict(db)
    db.refresh(user)
    return user


def list_staff(db: Session, *, role: UserRole | None, search: str | None,
               is_active: bool | None, page: int, page_size: int) -> tuple[list[User], int]:
    roles = [role] if role else list(STAFF_ROLES)
    return user_repository.list_users(
        db, roles=roles, search=search, is_active=is_active, page=page, page_size=page_size
    )


def get_staff(db: Session, user_id: uuid.UUID) -> User:
    return _get_user_with_role(db, user_id, STAFF_ROLES, "Admin")


def update_staff(db: Session, *, user_id: uuid.UUID, changes: dict) -> User:
    target = get_staff(db, user_id)

    new_email = changes.get("email")
    if new_email and new_email != target.email and user_repository.email_exists(db, new_email):
        raise AppException(message="An account with this email already exists", status_code=409)

    for field in ("name", "email"):  # explicit allow-list
        if field in changes:
            setattr(target, field, changes[field])

    auth_service.commit_or_conflict(db)
    db.refresh(target)
    return target


def set_staff_status(db: Session, *, actor: User, user_id: uuid.UUID, is_active: bool) -> User:
    target = get_staff(db, user_id)
    _ensure_not_self(actor, target, "account status")

    if not is_active and target.role == UserRole.SUPER_ADMIN:
        _lock_and_ensure_super_admin_remains(db, target)

    return _set_active(db, target, is_active)


def change_role(db: Session, *, actor: User, user_id: uuid.UUID, new_role: UserRole) -> User:
    if not can_assign_role(actor.role, new_role):
        raise AppException(message="You are not allowed to assign this role", status_code=403)

    target = user_repository.get_by_id(db, user_id)
    if target is None:
        raise _not_found("User")
    _ensure_not_self(actor, target, "role")

    if target.role == new_role:
        return target

    if target.role == UserRole.SUPER_ADMIN:
        _lock_and_ensure_super_admin_remains(db, target)

    target.role = new_role
    db.commit()
    db.refresh(target)
    return target


# =================================================== Customers (Admin + SA)
_CUSTOMER_ROLES = frozenset({UserRole.USER})


def list_customers(db: Session, *, search: str | None, is_active: bool | None,
                   page: int, page_size: int) -> tuple[list[User], int]:
    return user_repository.list_users(
        db, roles=[UserRole.USER], search=search, is_active=is_active, page=page, page_size=page_size
    )


def get_customer(db: Session, user_id: uuid.UUID) -> User:
    return _get_user_with_role(db, user_id, _CUSTOMER_ROLES, "Customer")


def set_customer_status(db: Session, *, user_id: uuid.UUID, is_active: bool) -> User:
    target = get_customer(db, user_id)
    return _set_active(db, target, is_active)
