import math
import uuid

from sqlalchemy.orm import Session

from app.core.response import success_response
from app.modules.admin import service
from app.modules.admin.schema import (
    AdminCreateRequest,
    AdminUpdateRequest,
    RoleUpdateRequest,
    StatusUpdateRequest,
)
from app.modules.user.model import User
from app.modules.user.roles import UserRole
from app.modules.user.schema import UserResponse


def _one(message: str, user: User):
    return success_response(message=message, data=UserResponse.model_validate(user))


def _page(message: str, users: list[User], total: int, page: int, page_size: int):
    return success_response(
        message=message,
        data=[UserResponse.model_validate(u) for u in users],
        meta={
            "page": page,
            "page_size": page_size,
            "total_records": total,
            "total_pages": math.ceil(total / page_size) if total else 0,
        },
    )


# ------------------------------------------------------------------- staff
def create_admin(db: Session, payload: AdminCreateRequest):
    user = service.create_admin(db, name=payload.name, email=payload.email, password=payload.password)
    return _one("Admin created successfully", user)


def list_staff(db: Session, role: UserRole | None, search: str | None,
               is_active: bool | None, page: int, page_size: int):
    users, total = service.list_staff(
        db, role=role, search=search, is_active=is_active, page=page, page_size=page_size
    )
    return _page("Admins fetched successfully", users, total, page, page_size)


def get_staff(db: Session, user_id: uuid.UUID):
    return _one("Admin fetched successfully", service.get_staff(db, user_id))


def update_staff(db: Session, user_id: uuid.UUID, payload: AdminUpdateRequest):
    user = service.update_staff(db, user_id=user_id, changes=payload.model_dump(exclude_unset=True))
    return _one("Admin updated successfully", user)


def set_staff_status(db: Session, actor: User, user_id: uuid.UUID, payload: StatusUpdateRequest):
    user = service.set_staff_status(db, actor=actor, user_id=user_id, is_active=payload.is_active)
    state = "activated" if user.is_active else "deactivated"
    return _one(f"Admin {state} successfully", user)


def change_role(db: Session, actor: User, user_id: uuid.UUID, payload: RoleUpdateRequest):
    user = service.change_role(db, actor=actor, user_id=user_id, new_role=payload.role)
    return _one("Role updated successfully", user)


# --------------------------------------------------------------- customers
def list_customers(db: Session, search: str | None, is_active: bool | None, page: int, page_size: int):
    users, total = service.list_customers(
        db, search=search, is_active=is_active, page=page, page_size=page_size
    )
    return _page("Customers fetched successfully", users, total, page, page_size)


def get_customer(db: Session, user_id: uuid.UUID):
    return _one("Customer fetched successfully", service.get_customer(db, user_id))


def set_customer_status(db: Session, user_id: uuid.UUID, payload: StatusUpdateRequest):
    user = service.set_customer_status(db, user_id=user_id, is_active=payload.is_active)
    state = "activated" if user.is_active else "deactivated"
    return _one(f"Customer {state} successfully", user)
