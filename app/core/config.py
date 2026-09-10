"""Application settings loaded from environment / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central config. Field names map case-insensitively to env vars."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_name: str = "SentiTrack AI"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    log_level: str = "INFO"
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Database ---
    database_url: str = "sqlite:///./sentitrack.db"

    # --- JWT ---
    jwt_secret_key: str = "please-change-me-to-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # --- OpenRouter ---
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Free-tier model IDs change on OpenRouter; keep these in sync with
    # https://openrouter.ai/collections/free-models (or set env overrides on Render).
    openrouter_model: str = "google/gemma-4-31b-it:free"
    openrouter_fallback_model: str = "google/gemma-4-26b-a4b-it:free"
    openrouter_timeout: float = 30.0
    openrouter_max_retries: int = 3

    # --- Cashfree (Phase 2 — server only; never expose to frontend) ---
    cashfree_env: str = "sandbox"  # sandbox | production
    cashfree_app_id: str = ""
    cashfree_secret_key: str = ""
    cashfree_webhook_secret: str = ""
    cashfree_api_version: str = "2023-08-01"
    cashfree_return_url: str = "https://sentitrackai.netlify.app/app/billing/return"
    cashfree_webhook_url: str = (
        "https://sentitrackai.onrender.com/api/v1/billing/cashfree/webhook"
    )

    # --- CORS ---
    cors_origins: list[str] = ["*"]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def cashfree_api_base(self) -> str:
        if self.cashfree_env.lower() == "production":
            return "https://api.cashfree.com/pg"
        return "https://sandbox.cashfree.com/pg"

    @property
    def cashfree_configured(self) -> bool:
        return bool(self.cashfree_app_id and self.cashfree_secret_key)

    @property
    def cashfree_signing_secret(self) -> str:
        # Cashfree PG docs sign with client secret; optional dedicated webhook secret preferred if set.
        return self.cashfree_webhook_secret or self.cashfree_secret_key


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
