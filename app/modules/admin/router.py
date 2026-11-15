"""
/admin endpoints.

Access is enforced at TWO levels:
  1. Route level: SuperAdminUser / StaffUser dependencies (401/403).
  2. Service level: self-modification, role-assignment and last-Super-Admin
     rules, plus target-role checks.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.response import ApiResponse
from app.database.dependencies import get_db
from app.modules.admin import controller
from app.modules.admin.schema import (
    AdminCreateRequest,
    AdminUpdateRequest,
    RoleUpdateRequest,
    StatusUpdateRequest,
)
from app.modules.auth.dependencies import StaffUser, SuperAdminUser
from app.modules.user.roles import UserRole
from app.modules.user.schema import UserResponse

router = APIRouter(prefix="/admin", tags=["Admin"])

DB = Annotated[Session, Depends(get_db)]
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]
Search = Annotated[str | None, Query(max_length=100)]


# ======================================================= SUPER_ADMIN only
@router.post("/admins", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[UserResponse])
def create_admin(payload: AdminCreateRequest, actor: SuperAdminUser, db: DB):
    return controller.create_admin(db, payload)


@router.get("/admins", response_model=ApiResponse[list[UserResponse]])
def list_admins(
    actor: SuperAdminUser,
    db: DB,
    role: Annotated[UserRole | None, Query(description="ADMIN or SUPER_ADMIN")] = None,
    search: Search = None,
    is_active: bool | None = None,
    page: Page = 1,
    page_size: PageSize = 20,
):
    return controller.list_staff(db, role, search, is_active, page, page_size)


@router.get("/admins/{user_id}", response_model=ApiResponse[UserResponse])
def get_admin(user_id: uuid.UUID, actor: SuperAdminUser, db: DB):
    return controller.get_staff(db, user_id)


@router.patch("/admins/{user_id}", response_model=ApiResponse[UserResponse])
def update_admin(user_id: uuid.UUID, payload: AdminUpdateRequest, actor: SuperAdminUser, db: DB):
    return controller.update_staff(db, user_id, payload)


@router.patch("/admins/{user_id}/status", response_model=ApiResponse[UserResponse])
def set_admin_status(user_id: uuid.UUID, payload: StatusUpdateRequest, actor: SuperAdminUser, db: DB):
    return controller.set_staff_status(db, actor, user_id, payload)


@router.patch(
    "/users/{user_id}/role",
    response_model=ApiResponse[UserResponse],
    summary="Change any account's role (promote/demote)",
)
def change_user_role(user_id: uuid.UUID, payload: RoleUpdateRequest, actor: SuperAdminUser, db: DB):
    return controller.change_role(db, actor, user_id, payload)


# ================================================ ADMIN and SUPER_ADMIN
@router.get("/customers", response_model=ApiResponse[list[UserResponse]])
def list_customers(
    actor: StaffUser,
    db: DB,
    search: Search = None,
    is_active: bool | None = None,
    page: Page = 1,
    page_size: PageSize = 20,
):
    return controller.list_customers(db, search, is_active, page, page_size)


@router.get("/customers/{user_id}", response_model=ApiResponse[UserResponse])
def get_customer(user_id: uuid.UUID, actor: StaffUser, db: DB):
    return controller.get_customer(db, user_id)


@router.patch("/customers/{user_id}/status", response_model=ApiResponse[UserResponse])
def set_customer_status(user_id: uuid.UUID, payload: StatusUpdateRequest, actor: StaffUser, db: DB):
    return controller.set_customer_status(db, user_id, payload)
