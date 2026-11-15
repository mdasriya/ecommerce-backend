"""
Central application configuration.

All settings come from environment variables (or the `.env` file in local
development). Real environment variables always take priority over `.env`,
which is what you want on a production server.

Usage anywhere in the app:
    from app.core.config import settings
    settings.DATABASE_URL
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root (the folder that contains `app/` and `.env`).
# Using an absolute path means `.env` is found no matter which folder
# you start uvicorn / alembic / pytest from.
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unrelated variables in .env
    )

    # ------------------------------------------------------------------ App
    APP_NAME: str = "E-commerce API"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"

    # ------------------------------------------------------------- Database
    DATABASE_URL: str

    # ------------------------------------------------------------------ JWT
    # SecretStr hides the value in logs/tracebacks/repr: prints as '**********'.
    # Read the real value with settings.JWT_SECRET_KEY.get_secret_value().
    JWT_SECRET_KEY: SecretStr = Field(min_length=32)
    JWT_ALGORITHM: Literal["HS256", "HS384", "HS512"] = "HS256"
    JWT_ISSUER: str = "ecommerce-api"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, ge=1, le=60)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, ge=1, le=90)

    # ----------------------------------------------------------------- CORS
    # JSON list in .env, e.g. CORS_ORIGINS=["http://localhost:3000"]
    CORS_ORIGINS: list[str] = []

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @model_validator(mode="after")
    def _check_production_safety(self) -> "Settings":
        if self.is_production and "*" in self.CORS_ORIGINS:
            raise ValueError(
                "CORS_ORIGINS must list explicit origins in production, not '*'."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    # lru_cache -> the .env file is read and validated only once.
    return Settings()


settings = get_settings()
