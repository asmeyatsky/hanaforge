"""Application settings — Pydantic BaseSettings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for the HanaForge infrastructure layer.

    All values are loaded from environment variables (or a .env file).
    """

    gcp_project_id: str = ""
    firestore_database: str = "(default)"
    gcs_bucket: str = ""
    anthropic_api_key: str = ""
    google_ai_api_key: str = ""
    sap_default_host: str = ""

    # Auth
    auth_enabled: bool = False
    jwt_secret: str = "hanaforge-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60

    # Persistence
    use_firestore: bool = False

    # Logging
    log_level: str = "INFO"
    log_format: str = "text"  # "json" for production, "text" for dev

    model_config = {
        "env_prefix": "HANAFORGE_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of application settings."""
    return Settings()
