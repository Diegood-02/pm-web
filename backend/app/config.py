"""Configuración de la aplicación leída desde variables de entorno.

Los secretos no tienen valor por defecto: si falta DATABASE_URL o JWT_SECRET_KEY,
la aplicación no arranca. Así nunca corre con una clave conocida por error.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = Field(min_length=10)
    jwt_secret_key: str = Field(min_length=32)
    jwt_access_token_minutes: int = Field(default=30, ge=1, le=1440)
    jwt_refresh_token_days: int = Field(default=7, ge=1, le=90)
    cors_allowed_origins: str = "http://localhost:5173"
    default_timezone: str = "America/Mexico_City"
    log_level: str = "INFO"
    max_request_bytes: int = Field(default=2_000_000, ge=1024)
    max_tasks_per_project: int = Field(default=5000, ge=1)
    login_max_failures: int = Field(default=5, ge=1)
    login_window_minutes: int = Field(default=15, ge=1)

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
