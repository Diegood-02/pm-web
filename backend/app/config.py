"""Configuración de la aplicación leída desde variables de entorno."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    database_url: str = "postgresql+psycopg://pm:cambia-esta-clave@localhost:5432/pm_web"
    jwt_secret_key: str = Field(min_length=16)
    jwt_access_token_minutes: int = 30
    jwt_refresh_token_days: int = 7
    cors_allowed_origins: str = "http://localhost:5173"
    default_timezone: str = "America/Mexico_City"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
