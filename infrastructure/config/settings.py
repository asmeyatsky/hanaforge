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

    model_config = {
        "env_prefix": "HANAFORGE_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton of application settings."""
    return Settings()
