from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Create database engine.
# pool_pre_ping=True checks a pooled connection is alive before using it.
# Important for Neon, which closes idle connections when the compute sleeps.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)
