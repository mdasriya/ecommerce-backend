"""
Alembic environment.

- The database URL comes from app settings (.env / environment variables),
  never from alembic.ini.
- target_metadata = our SQLAlchemy Base.metadata, so `alembic revision
  --autogenerate` can compare models against the real database.
- A caller (e.g. the test suite) may pass an already-open connection through
  `config.attributes["connection"]`; then that connection is used instead.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.core.config import settings
from app.database.base import Base

# Importing the registry registers every model on Base.metadata.
# If a model is not imported there, autogenerate thinks its table should be DROPPED.
import app.database.init_db  # noqa: F401

config = context.config

if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _configure(**kwargs) -> None:
    context.configure(
        target_metadata=target_metadata,
        compare_type=True,            # detect column type changes
        compare_server_default=True,  # detect server default changes
        **kwargs,
    )


def run_migrations_offline() -> None:
    """`alembic upgrade --sql`: print SQL instead of executing it."""
    _configure(
        url=settings.DATABASE_URL,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    existing_connection = config.attributes.get("connection")

    if existing_connection is not None:
        _configure(connection=existing_connection)
        with context.begin_transaction():
            context.run_migrations()
        return

    # NullPool: a migration is a one-off process, no need to keep connections.
    connectable = create_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        _configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
