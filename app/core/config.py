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

    # If two requests (e.g. two browser tabs opening at once) present the SAME
    # refresh token within this many seconds, the second one is treated as a
    # harmless race instead of token theft. 0 disables the grace window.
    REFRESH_TOKEN_REUSE_GRACE_SECONDS: int = Field(default=30, ge=0, le=120)

    # ------------------------------------------------------- Refresh cookie
    # The refresh token lives ONLY in an HttpOnly cookie in the browser.
    # Defaults suit a frontend and API on DIFFERENT sites over HTTPS
    # (e.g. Vercel + Render): SameSite=None requires Secure.
    # Local development over plain http (localhost:5173 -> localhost:8000 is
    # the SAME site) can use: REFRESH_COOKIE_SECURE=false, REFRESH_COOKIE_SAMESITE=lax
    REFRESH_COOKIE_NAME: str = "refresh_token"
    REFRESH_COOKIE_SECURE: bool = True
    REFRESH_COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "none"
    REFRESH_COOKIE_PATH: str = "/"

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
        if self.REFRESH_COOKIE_SAMESITE == "none" and not self.REFRESH_COOKIE_SECURE:
            raise ValueError(
                "REFRESH_COOKIE_SAMESITE=none requires REFRESH_COOKIE_SECURE=true "
                "(browsers reject SameSite=None cookies that are not Secure)."
            )
        if self.is_production and not self.REFRESH_COOKIE_SECURE:
            raise ValueError("REFRESH_COOKIE_SECURE must be true in production.")
        return self

    @property
    def refresh_token_max_age_seconds(self) -> int:
        return self.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


@lru_cache
def get_settings() -> Settings:
    # lru_cache -> the .env file is read and validated only once.
    return Settings()


settings = get_settings()
