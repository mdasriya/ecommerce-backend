"""
Controllers: call the service, shape the data, wrap it in the common
success_response format. No business rules here.
"""

from sqlalchemy.orm import Session

from app.core.response import success_response
from app.modules.auth import service
from app.modules.auth.schema import (
    AuthResponse,
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateMeRequest,
)
from app.modules.user.model import User
from app.modules.user.schema import UserResponse


def _auth_payload(user: User, tokens: service.IssuedTokens) -> AuthResponse:
    return AuthResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        expires_in=tokens.expires_in,
        user=UserResponse.model_validate(user),
    )


def register(db: Session, payload: RegisterRequest):
    user = service.register(db, name=payload.name, email=payload.email, password=payload.password)
    return success_response(message="Registration successful", data=UserResponse.model_validate(user))


def login(db: Session, payload: LoginRequest):
    user, tokens = service.login(db, email=payload.email, password=payload.password)
    return success_response(message="Login successful", data=_auth_payload(user, tokens))


def refresh(db: Session, payload: RefreshRequest):
    user, tokens = service.refresh(db, raw_refresh_token=payload.refresh_token)
    return success_response(message="Token refreshed successfully", data=_auth_payload(user, tokens))


def logout(db: Session, raw_refresh_token: str | None):
    # No token (cookie already gone) -> nothing to revoke; still a success so
    # logout is idempotent.
    if raw_refresh_token:
        service.logout(db, raw_refresh_token=raw_refresh_token)
    return success_response(message="Logged out successfully")


def get_me(user: User):
    return success_response(message="Profile fetched successfully", data=UserResponse.model_validate(user))


def update_me(db: Session, user: User, payload: UpdateMeRequest):
    updated = service.update_me(db, user=user, changes=payload.model_dump(exclude_unset=True))
    return success_response(message="Profile updated successfully", data=UserResponse.model_validate(updated))


def change_password(db: Session, user: User, payload: ChangePasswordRequest):
    tokens = service.change_password(
        db,
        user=user,
        current_password=payload.current_password,
        new_password=payload.new_password,
    )
    return success_response(
        message="Password changed successfully. All other sessions have been signed out.",
        data=TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            expires_in=tokens.expires_in,
        ),
    )
