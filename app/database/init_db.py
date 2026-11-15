"""
Model registry.

Import EVERY SQLAlchemy model here. Alembic (migrations/env.py) imports this
module so that all tables are registered on Base.metadata before it compares
models with the database.

Tables are created/changed ONLY through Alembic migrations:
    alembic upgrade head
The app no longer calls Base.metadata.create_all() on startup, because
create_all can create missing tables but can never alter existing ones,
which silently leaves the database out of sync with the models.
"""

from app.database.base import Base  # noqa: F401
from app.modules.category.model import Category  # noqa: F401
from app.modules.user.model import User  # noqa: F401
from app.modules.auth.model import RefreshToken  # noqa: F401
