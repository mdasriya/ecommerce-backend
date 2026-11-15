"""
/auth endpoints.

Every endpoint declares `response_model=ApiResponse[...]`: FastAPI then
validates and FILTERS the output, so only whitelisted fields are ever sent.

Refresh-token transport (browsers):
  login / refresh / change-password  -> Set-Cookie (HttpOnly) with the token
  refresh / logout                   -> token read from that cookie
The cookie attributes come from ONE helper, so setting and deleting always
match (a browser only deletes a cookie whose name/path/attributes match).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.response import ApiResponse, error_response
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

NO_REFRESH_TOKEN = "No refresh token"


def _cookie_attributes() -> dict[str, Any]:
    return {
        "key": settings.REFRESH_COOKIE_NAME,
        "path": settings.REFRESH_COOKIE_PATH,
        "secure": settings.REFRESH_COOKIE_SECURE,
        "httponly": True,
        "samesite": settings.REFRESH_COOKIE_SAMESITE,
    }


def _set_refresh_token_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        value=token,
        max_age=settings.refresh_token_max_age_seconds,
        **_cookie_attributes(),
    )


def _clear_refresh_token_cookie(response: Response) -> None:
    response.delete_cookie(**_cookie_attributes())


def _read_refresh_token_cookie(request: Request) -> str | None:
    return request.cookies.get(settings.REFRESH_COOKIE_NAME) or None


def _no_store(response: Response) -> None:
    # Responses containing tokens must never be cached by browsers/proxies.
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"


def _invalid_session_response(message: str) -> JSONResponse:
    """
    401 for a refresh that can never succeed. The dead cookie is deleted in the
    SAME response, so the browser stops sending it on every page load.
    (Raising an exception instead would discard any Set-Cookie header.)
    """
    response = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content=error_response(message=message),
        headers={"WWW-Authenticate": "Bearer"},
    )
    _no_store(response)
    _clear_refresh_token_cookie(response)
    return response


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
    result = controller.login(db, payload)
    # result is a plain dict; result["data"] is an AuthResponse MODEL,
    # so its fields are attributes (not subscriptable).
    _set_refresh_token_cookie(response, result["data"].refresh_token)
    return result


@router.post("/refresh", response_model=ApiResponse[AuthResponse])
def refresh(request: Request, response: Response, db: DB):
    """Rotate the refresh token from the HttpOnly cookie; return a new access token."""
    _no_store(response)

    refresh_token = _read_refresh_token_cookie(request)
    if not refresh_token:
        return _invalid_session_response(NO_REFRESH_TOKEN)

    try:
        result = controller.refresh(db, RefreshRequest(refresh_token=refresh_token))
    except AppException as exc:
        if exc.status_code == status.HTTP_401_UNAUTHORIZED:
            return _invalid_session_response(exc.message)
        raise

    _set_refresh_token_cookie(response, result["data"].refresh_token)
    return result


@router.post("/logout", response_model=ApiResponse[None])
def logout(
    request: Request,
    response: Response,
    db: DB,
    payload: LogoutRequest | None = None,
):
    """
    No access token required: users must be able to log out even after their
    15-minute access token has expired. The cookie is the source of truth for
    browsers; the optional body supports non-browser clients.
    """
    _no_store(response)
    raw_refresh_token = _read_refresh_token_cookie(request) or (
        payload.refresh_token if payload else None
    )
    result = controller.logout(db, raw_refresh_token)
    _clear_refresh_token_cookie(response)
    return result


@router.get("/me", response_model=ApiResponse[UserResponse])
def get_me(user: CurrentUser):
    return controller.get_me(user)


@router.patch("/me", response_model=ApiResponse[UserResponse])
def update_me(payload: UpdateMeRequest, user: CurrentUser, db: DB):
    return controller.update_me(db, user, payload)


@router.post("/change-password", response_model=ApiResponse[TokenResponse])
def change_password(payload: ChangePasswordRequest, response: Response, user: CurrentUser, db: DB):
    _no_store(response)
    result = controller.change_password(db, user, payload)
    # All sessions were revoked, including the one in this browser's cookie;
    # store the fresh refresh token so this device stays signed in.
    _set_refresh_token_cookie(response, result["data"].refresh_token)
    return result
