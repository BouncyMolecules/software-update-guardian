"""Package configuration via environment and settings."""

from __future__ import annotations

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and optional ``.env`` file."""

    model_config = SettingsConfigDict(
        env_prefix="UPDATE_GUARDIAN_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    log_level: str = Field(default="INFO", description="Root log level for the application.")
    database_url: str = Field(
        default="sqlite:///./data/update_guardian.db",
        description="SQLAlchemy database URL; SQLite file paths are resolved relative to CWD.",
    )
    organization_name: str | None = Field(
        default=None,
        description="Optional display name for audit banners in exports and UI.",
    )

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        upper = value.strip().upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if upper not in allowed:
            msg = f"log_level must be one of {sorted(allowed)}"
            raise ValueError(msg)
        return upper


def get_settings() -> Settings:
    """Factory for settings (allows tests to patch ``get_settings`` if needed)."""
    return Settings()
