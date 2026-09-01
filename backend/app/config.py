"""Environment-driven settings (pydantic-settings).

Nothing in the app reads `os.environ` directly -- everything goes through
`settings` so tests can override a single object.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False
    )

    # --- LLM ---
    google_api_key: str = ""
    gemini_model: str = "gemini-3.6-flash"
    gemini_extraction_model: str = "gemini-3.5-flash-lite"
    #: Step-1 scaffold switch. Also forced on whenever GOOGLE_API_KEY is absent.
    use_mock_llm: bool = True

    # --- Embeddings (Gemini API; no model is downloaded by the server) ---
    embedding_model: str = "gemini-embedding-001"
    embedding_dimensions: int = 768
    embedding_max_chars: int = 7_000
    next_public_supabase_url: str = ""
    next_public_supabase_publishable_key: str = ""

    # --- Security ---
    session_ttl_days: int = 30

    # --- Database ---
    database_url: str = "sqlite:///./vacancyscore.db"

    # --- Runtime ---
    environment: Literal["dev", "production"] = "dev"
    port: int = 8000
    allowed_origins: str = "http://localhost:3000"
    public_app_url: str = "http://localhost:3000"
    # Vercel provides this automatically in its function runtime.
    vercel: bool = False

    # --- Abuse protection ---
    analyze_daily_limit: int = 10
    max_cvs_per_user: int = 10
    max_vacancy_chars: int = 15_000
    # Keep headroom under Vercel's request-body limit.
    max_upload_bytes: int = 4 * 1024 * 1024

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def cookie_secure(self) -> bool:
        # Production cookies are Secure.
        return self.is_production

    @property
    def cookie_samesite(self) -> Literal["lax", "none"]:
        return "lax"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.google_api_key) and not self.use_mock_llm


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
