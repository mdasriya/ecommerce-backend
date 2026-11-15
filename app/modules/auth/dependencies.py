"""
Authentication & authorization dependencies.

Usage in any router:

    from app.modules.auth.dependencies import CurrentUser, require_roles, require_staff

    @router.get("/me")
    def me(user: CurrentUser): ...                         # any logged-in user

    @router.post("/", dependencies=[Depends(require_staff)])
    def create_product(...): ...                            # ADMIN or SUPER_ADMIN

    @router.post("/admins")
    def create_admin(actor: Annotated[User, Depends(require_super_admin)]): ...
"""

from typing import Annotated, Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core import security
from app.core.exceptions import AppException
from app.database.dependencies import get_db
from app.modules.user import repository as user_repository
from app.modules.user.model import User
from app.modules.user.roles import STAFF_ROLES, UserRole

# auto_error=False: we raise our own 401 so the response uses the common
# format and the correct status (HTTPBearer's default is a bare 403).
# This also makes Swagger show the "Authorize" button (paste the access token).
_bearer_scheme = HTTPBearer(auto_error=False, description="Paste the access_token from /auth/login")


def _unauthorized(message: str) -> AppException:
    return AppException(message=message, status_code=401, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """
    1. Require an `Authorization: Bearer <token>` header.
    2. Verify the JWT (signature, expiry, issuer, type == access).
    3. Load the user FROM THE DATABASE (fresh role + active status).
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Not authenticated")

    try:
        user_id = security.decode_access_token(credentials.credentials)
    except security.TokenError as exc:
        raise _unauthorized(str(exc)) from exc

    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise _unauthorized("Invalid authentication credentials")

    if not user.is_active:
        raise AppException(message="Account is deactivated", status_code=403)

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*allowed_roles: UserRole) -> Callable[..., User]:
    """
    Dependency factory: only users whose role is in `allowed_roles` pass.
    401 = not logged in / bad token; 403 = logged in but not allowed.
    """
    allowed = frozenset(allowed_roles)

    def _role_checker(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise AppException(
                message="You do not have permission to perform this action",
                status_code=403,
            )
        return user

    return _role_checker


require_super_admin = require_roles(UserRole.SUPER_ADMIN)
require_staff = require_roles(*STAFF_ROLES)

SuperAdminUser = Annotated[User, Depends(require_super_admin)]
StaffUser = Annotated[User, Depends(require_staff)]
