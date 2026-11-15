"""
Reusable user field types + the public user response.

SECURITY: UserResponse is a WHITELIST. Only these fields can ever leave the
API for a user object; password_hash is simply not in it. Every endpoint that
returns a user uses `response_model=...UserResponse...`, so even if a
controller accidentally passes the ORM object, FastAPI strips other fields.
"""

import re
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, StringConstraints

from app.modules.user.roles import UserRole

PASSWORD_MIN_LENGTH = 8
# Upper bound prevents abuse: hashing a multi-megabyte "password" with Argon2
# would let an attacker burn server CPU/RAM with a few requests.
PASSWORD_MAX_LENGTH = 128


def normalize_email(value: str) -> str:
    # EmailStr already validated the format. We lower-case the WHOLE address
    # so John@Example.com and john@example.com are the same account.
    return value.strip().lower()


def validate_password_strength(value: str) -> str:
    # NOTE: passwords are never stripped/modified; spaces are allowed.
    problems = []
    if len(value) < PASSWORD_MIN_LENGTH:
        problems.append(f"at least {PASSWORD_MIN_LENGTH} characters")
    if not re.search(r"[a-z]", value):
        problems.append("a lowercase letter")
    if not re.search(r"[A-Z]", value):
        problems.append("an uppercase letter")
    if not re.search(r"\d", value):
        problems.append("a number")
    if value.strip() == "":
        problems.append("non-whitespace characters")

    if problems:
        raise ValueError("Password must contain " + ", ".join(problems) + ".")
    return value


def validate_name(value: str) -> str:
    value = " ".join(value.split())  # trim + collapse internal whitespace
    if not value:
        raise ValueError("Name cannot be empty.")
    if any(ord(ch) < 32 for ch in value):
        raise ValueError("Name contains invalid characters.")
    return value


# ---- Reusable annotated field types --------------------------------------
EmailField = Annotated[EmailStr, StringConstraints(max_length=255), AfterValidator(normalize_email)]

NewPasswordField = Annotated[
    str,
    StringConstraints(max_length=PASSWORD_MAX_LENGTH),
    AfterValidator(validate_password_strength),
]

# For login / "current password": no strength rules (old accounts may predate
# the rules), only a length cap.
PasswordInputField = Annotated[str, StringConstraints(min_length=1, max_length=PASSWORD_MAX_LENGTH)]

NameField = Annotated[str, StringConstraints(max_length=100), AfterValidator(validate_name)]


# ---- Base for every request body ------------------------------------------
class StrictRequest(BaseModel):
    """
    extra="forbid": unknown fields are REJECTED (422) instead of ignored.
    This blocks "mass assignment" attacks such as sending
    {"role": "SUPER_ADMIN"} or {"is_active": true} to an endpoint that should
    never accept them.
    """

    model_config = ConfigDict(extra="forbid")


# ---- Responses ------------------------------------------------------------
class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
