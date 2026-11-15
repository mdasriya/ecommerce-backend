from typing import Annotated, Literal

from pydantic import BaseModel, StringConstraints, model_validator

from app.modules.user.schema import (
    EmailField,
    NameField,
    NewPasswordField,
    PasswordInputField,
    StrictRequest,
    UserResponse,
)

# Our refresh tokens are ~86 chars; cap input size defensively.
RefreshTokenField = Annotated[str, StringConstraints(min_length=1, max_length=256)]


# ------------------------------------------------------------------ Requests
class RegisterRequest(StrictRequest):
    """
    There is deliberately NO `role` field, and StrictRequest forbids extra
    fields, so {"role": "ADMIN"} is rejected with 422. Public registration
    always creates a USER.
    """

    name: NameField
    email: EmailField
    password: NewPasswordField


class LoginRequest(StrictRequest):
    email: EmailField
    password: PasswordInputField


class RefreshRequest(StrictRequest):
    refresh_token: str | None = None


class LogoutRequest(StrictRequest):
    """
    Browsers send NO body: the refresh token is read from the HttpOnly cookie
    (JavaScript cannot read it). The body field remains for non-browser
    clients (Swagger, scripts) that hold the token themselves.
    """

    refresh_token: RefreshTokenField | None = None


class UpdateMeRequest(StrictRequest):
    """
    Only `name` for now. Changing EMAIL is intentionally not allowed yet:
    without email verification, a stolen session could switch the account's
    email and lock out the real owner. Add it together with verification.
    """

    name: NameField | None = None

    @model_validator(mode="after")
    def _at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Name cannot be null.")
        return self


class ChangePasswordRequest(StrictRequest):
    current_password: PasswordInputField
    new_password: NewPasswordField

    @model_validator(mode="after")
    def _new_differs_from_current(self):
        if self.new_password == self.current_password:
            raise ValueError("New password must be different from the current password.")
        return self


# ----------------------------------------------------------------- Responses
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int  # access-token lifetime in seconds


class AuthResponse(TokenResponse):
    user: UserResponse
