from pydantic import StrictBool, model_validator

from app.modules.user.roles import UserRole
from app.modules.user.schema import EmailField, NameField, NewPasswordField, StrictRequest


class AdminCreateRequest(StrictRequest):
    """Always creates role=ADMIN. Promotion to SUPER_ADMIN is a separate,
    explicit role change (PATCH /admin/users/{id}/role)."""

    name: NameField
    email: EmailField
    password: NewPasswordField


class AdminUpdateRequest(StrictRequest):
    """Permitted admin info only. role / is_active / password have their own
    dedicated endpoints and are rejected here (extra="forbid")."""

    name: NameField | None = None
    email: EmailField | None = None

    @model_validator(mode="after")
    def _validate(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} cannot be null.")
        return self


class StatusUpdateRequest(StrictRequest):
    # StrictBool: only JSON true/false accepted (not "yes", 1, "true").
    is_active: StrictBool


class RoleUpdateRequest(StrictRequest):
    role: UserRole
