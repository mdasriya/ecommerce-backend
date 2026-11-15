from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Deterministic constraint names.
# Without this, some constraints get random/database-chosen names and Alembic
# can't reliably alter or drop them in future migrations.
# These templates match PostgreSQL's own default naming style, so they also
# match the constraints that already exist on the `categories` table.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "%(table_name)s_%(column_0_name)s_key",
    "ck": "%(table_name)s_%(constraint_name)s_check",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """
    Adds created_at / updated_at to a model.

    - timezone=True -> PostgreSQL TIMESTAMPTZ (always store time zone-aware UTC).
    - server_default=now() -> the DATABASE sets the value, so it is correct
      even for rows inserted outside the app (CLI, SQL console).
    - onupdate=now() -> SQLAlchemy sets updated_at on every ORM UPDATE.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
