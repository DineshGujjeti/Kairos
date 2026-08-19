"""
Centralized application configuration.

Every setting the app needs is declared here, typed, and validated at
startup via Pydantic. Nothing in the codebase should call
os.environ.get(...) directly -- if a new setting is needed, add it here.
This keeps configuration auditable in one place and fails fast (at
boot, not mid-request) if something required is missing or malformed.
"""
from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- App metadata ---
    PROJECT_NAME: str = "Kairos"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"  # development | staging | production
    DEBUG: bool = True

    # --- Security ---
    SECRET_KEY: str  # required, no default -- must be set in .env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- Database (PostgreSQL - transactional store) ---
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "kairos"
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = "kairos"
    # Plain str, not PostgresDsn: intentionally loose so the test suite
    # (tests/conftest.py) can override it with a sqlite:// URL.
    # Production always gets a real postgresql+psycopg:// URL, either
    # assembled below from POSTGRES_* or passed explicitly.
    DATABASE_URL: str | None = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str | None, info) -> str:
        if isinstance(v, str) and v:
            return v
        data = info.data
        return (
            f"postgresql+psycopg://{data.get('POSTGRES_USER')}:"
            f"{data.get('POSTGRES_PASSWORD')}@{data.get('POSTGRES_SERVER')}:"
            f"{data.get('POSTGRES_PORT')}/{data.get('POSTGRES_DB')}"
        )

    # --- DuckDB (analytical store over uploaded files) ---
    DUCKDB_PATH: str = "./data/duckdb/kairos_analytics.duckdb"
    DATASET_STORAGE_DIR: str = "./data/uploads"

    # --- Dataset ingestion (Module 2) ---
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = ["csv", "xls", "xlsx"]

    @field_validator("ALLOWED_UPLOAD_EXTENSIONS", mode="before")
    @classmethod
    def assemble_upload_extensions(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip().lower() for i in v.split(",") if i.strip()]
        return v

    # --- CORS ---
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    # --- Logging ---
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = True

    # --- AI (Gemini) / Module 6 ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"
    GEMINI_TIMEOUT: int = 60
    GEMINI_MAX_RETRIES: int = 3


@lru_cache
def get_settings() -> Settings:
    """
    Settings are cached (singleton) for the lifetime of the process --
    avoids re-parsing/re-validating the environment on every request.
    """
    return Settings()


settings = get_settings()
