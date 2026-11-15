"""
One-time bootstrap: create the FIRST Super Admin.

    python -m app.cli.create_super_admin
    python -m app.cli.create_super_admin --email you@company.com --name "Your Name"

Inputs (first match wins):
  email    --email      | SUPER_ADMIN_EMAIL    | interactive prompt
  name     --name       | SUPER_ADMIN_NAME     | interactive prompt
  password SUPER_ADMIN_PASSWORD (non-interactive deploys only) | hidden prompt (asked twice)

The password is deliberately NOT accepted as a command-line argument:
arguments are visible to other users via the process list and end up in
shell history.

Why this can't be abused:
  * It is not an HTTP endpoint; it needs shell access + the DATABASE_URL.
  * It REFUSES to run if any Super Admin already exists (active or not).
    After the first one, new Super Admins are only created/promoted through
    the authenticated, Super-Admin-only API.
  * A PostgreSQL advisory lock serialises concurrent runs, so two people
    running it at the same moment can't both create one.
"""

import argparse
import getpass
import os
import sys

from pydantic import ValidationError
from sqlalchemy import text

from app.core.exceptions import AppException
from app.database.connection import SessionLocal
from app.modules.auth import service as auth_service
from app.modules.user import repository as user_repository
from app.modules.user.roles import UserRole
from app.modules.user.schema import EmailField, NameField, NewPasswordField, StrictRequest

# Arbitrary fixed 64-bit number identifying "the bootstrap lock".
_BOOTSTRAP_LOCK_KEY = 7_431_902_001


class _BootstrapInput(StrictRequest):
    # Same validation rules as the API (email format, password strength...).
    name: NameField
    email: EmailField
    password: NewPasswordField


def _fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def _read_password() -> str:
    env_password = os.getenv("SUPER_ADMIN_PASSWORD")
    if env_password:
        print("Using password from SUPER_ADMIN_PASSWORD. Remove that variable after this run.")
        return env_password

    if not sys.stdin.isatty():
        _fail("No terminal for a password prompt. Set SUPER_ADMIN_PASSWORD for non-interactive use.")

    first = getpass.getpass("Password: ")
    second = getpass.getpass("Confirm password: ")
    if first != second:
        _fail("Passwords do not match.")
    return first


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Create the first Super Admin account.")
    parser.add_argument("--email")
    parser.add_argument("--name")
    args = parser.parse_args(argv)

    email = args.email or os.getenv("SUPER_ADMIN_EMAIL") or input("Email: ")
    name = args.name or os.getenv("SUPER_ADMIN_NAME") or input("Name: ")
    password = _read_password()

    try:
        data = _BootstrapInput(name=name, email=email, password=password)
    except ValidationError as exc:
        # Print field + message only, never the submitted values.
        for err in exc.errors():
            field = ".".join(str(p) for p in err["loc"])
            print(f"  {field}: {err['msg'].removeprefix('Value error, ')}", file=sys.stderr)
        _fail("Invalid input.")

    with SessionLocal() as db:
        # Transaction-scoped lock: released automatically on commit/rollback.
        # (Works through Neon's PgBouncer pooler, unlike session-level locks.)
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": _BOOTSTRAP_LOCK_KEY})

        if user_repository.super_admin_exists(db):
            db.rollback()
            _fail(
                "A Super Admin already exists. Bootstrap is disabled. "
                "Log in as a Super Admin and use the admin API instead."
            )

        if user_repository.email_exists(db, data.email):
            # Never silently promote an existing account.
            db.rollback()
            _fail("An account with this email already exists. Use a different email.")

        try:
            user = auth_service.create_user_account(
                db,
                name=data.name,
                email=data.email,
                password=data.password,
                role=UserRole.SUPER_ADMIN,
            )
            auth_service.commit_or_conflict(db)
        except AppException as exc:
            db.rollback()
            _fail(exc.message)

        print(f"Super Admin created: {user.email} (id={user.id})")


if __name__ == "__main__":
    main()
