"""
Single source of truth for user roles.

To add a future role (e.g. VENDOR):
  1. Add it to UserRole.
  2. Decide which groups below it belongs to / who may assign it.
  3. Create an Alembic migration that updates the `users_role_check`
     CHECK constraint (autogenerate does NOT detect CHECK changes).
No authentication code needs to change.
"""

from enum import StrEnum


class UserRole(StrEnum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    USER = "USER"


# Staff = people who operate the store (catalogue, orders, customers).
STAFF_ROLES: frozenset[UserRole] = frozenset({UserRole.SUPER_ADMIN, UserRole.ADMIN})

# Which roles each role is allowed to ASSIGN to other accounts.
# Only SUPER_ADMIN can change roles. ADMIN cannot create/promote anyone,
# so privilege escalation through role assignment is impossible for them.
ASSIGNABLE_ROLES: dict[UserRole, frozenset[UserRole]] = {
    UserRole.SUPER_ADMIN: frozenset(UserRole),
    UserRole.ADMIN: frozenset(),
    UserRole.USER: frozenset(),
}


def can_assign_role(actor_role: UserRole, target_role: UserRole) -> bool:
    return target_role in ASSIGNABLE_ROLES.get(actor_role, frozenset())
