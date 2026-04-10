"""
Configuration loader using pydantic-settings.
Loads environment variables from .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration from environment variables."""

    # Supabase
    supabase_url: str
    supabase_service_key: str

    # Postgres
    database_url: str

    # Qdrant vector DB
    qdrant_url: str
    qdrant_api_key: str
    qdrant_collection: str

    # LLM APIs
    google_ai_api_key: str
    anthropic_api_key: str
    openai_api_key: str

    # WhatsApp (WATI)
    wati_api_url: str
    wati_api_key: str
    wati_phone_number: str = ""  # Optional: WhatsApp phone number

    # Google Drive OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = ""

    # GitHub connector (optional)
    github_pat: str = ""  # Personal access token — empty disables GitHub connector

    # App security
    app_secret_key: str

    # Environment
    environment: str = "development"  # development, staging, production

    # Monitoring
    sentry_dsn: str = ""  # Optional: Sentry error tracking DSN

    model_config = SettingsConfigDict(env_file=".env")

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def workers(self) -> int:
        """Number of uvicorn workers — 4 in production, 1 in development."""
        return 4 if self.is_production else 1


# Global settings instance
settings = Settings()
