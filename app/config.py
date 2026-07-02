"""
Application settings, loaded from environment variables / .env file.

v1 scope: no Redis, no rate limiting. See SPEC.md Section 0.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Application ---
    environment: str = "development"
    log_level: str = "INFO"

    # --- Security ---
    secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24  # 24 hours, per spec

    # --- Database ---
    database_url: str

    # --- CORS ---
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


# Singleton settings instance, imported throughout the app
settings = Settings()
