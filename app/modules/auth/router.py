"""
/auth endpoints.

Every endpoint declares `response_model=ApiResponse[...]`: FastAPI then
validates and FILTERS the output, so only whitelisted fields are ever sent.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.response import ApiResponse
from app.database.dependencies import get_db
from app.modules.auth import controller
from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.schema import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateMeRequest,
)
from app.modules.user.schema import UserResponse

router = APIRouter(prefix="/auth", tags=["Auth"])

DB = Annotated[Session, Depends(get_db)]


def _no_store(response: Response) -> None:
    # Responses containing tokens must never be cached by browsers/proxies.
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=ApiResponse[UserResponse],
    summary="Register a new customer account (role is always USER)",
)
def register(payload: RegisterRequest, db: DB):
    return controller.register(db, payload)


@router.post("/login", response_model=ApiResponse[AuthResponse])
def login(payload: LoginRequest, response: Response, db: DB):
    _no_store(response)
    return controller.login(db, payload)


@router.post("/refresh", response_model=ApiResponse[AuthResponse])
def refresh(payload: RefreshRequest, response: Response, db: DB):
    _no_store(response)
    return controller.refresh(db, payload)


@router.post("/logout", response_model=ApiResponse[None])
def logout(payload: LogoutRequest, db: DB):
    # No access token required: users must be able to log out even after
    # their 15-minute access token has expired.
    return controller.logout(db, payload)


@router.get("/me", response_model=ApiResponse[UserResponse])
def get_me(user: CurrentUser):
    return controller.get_me(user)


@router.patch("/me", response_model=ApiResponse[UserResponse])
def update_me(payload: UpdateMeRequest, user: CurrentUser, db: DB):
    return controller.update_me(db, user, payload)


@router.post("/change-password", response_model=ApiResponse[TokenResponse])
def change_password(payload: ChangePasswordRequest, response: Response, user: CurrentUser, db: DB):
    _no_store(response)
    return controller.change_password(db, user, payload)
