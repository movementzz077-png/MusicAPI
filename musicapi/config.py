from functools import lru_cache
import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


class Settings(BaseSettings):
    spotify_client_id: str | None = Field(default=None, alias="SPOTIFY_CLIENT_ID")
    spotify_client_secret: str | None = Field(default=None, alias="SPOTIFY_CLIENT_SECRET")
    app_host: str = Field(default="127.0.0.1", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    database_path: str = Field(default=str(ROOT_DIR / "musicapi.sqlite3"), alias="DATABASE_PATH")
    cache_ttl_seconds: int = Field(default=60 * 60 * 24 * 7, alias="CACHE_TTL_SECONDS")
    audio_url_ttl_seconds: int = Field(default=60 * 45, alias="AUDIO_URL_TTL_SECONDS")
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")
    ytdlp_cookies_file: str | None = Field(default=None, alias="YTDLP_COOKIES_FILE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    debug: bool = Field(default=False, alias="APP_DEBUG")

    model_config = SettingsConfigDict(env_file=str(ROOT_DIR / ".env"), extra="ignore")

    @property
    def spotify_enabled(self) -> bool:
        return bool(self.spotify_client_id and self.spotify_client_secret)

    @property
    def runtime_port(self) -> int:
        return int(os.getenv("PORT") or self.app_port)

    @property
    def allowed_origins(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return origins or ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
