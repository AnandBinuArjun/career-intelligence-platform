from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parents[4]
_ENV_CANDIDATES = (str(_REPO_ROOT / ".env"), ".env")

_DISALLOWED_PROD_SECRETS = {
    "development-only-change-this-secret",
    "replace-with-a-long-random-secret",
    "change-me-local-only",
    "local-admin-only",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_CANDIDATES, extra="ignore")

    app_name: str = "Career Intelligence Platform"
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"
    database_url: str = (
        "postgresql+psycopg://career_app:change-me-local-only@localhost:5432/career_intelligence"
    )
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret_key: str = "development-only-change-this-secret"
    jwt_algorithm: str = "HS256"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7
    cookie_secure: bool = False
    rate_limit_enabled: bool = True

    storage_backend: str = "s3"  # "s3" or "local"
    local_storage_dir: str = ".private_storage"
    max_upload_mb: int = 10
    max_docx_uncompressed_mb: int = 50
    allowed_upload_types: str = (
        "application/pdf,"
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document,"
        "text/plain"
    )
    s3_endpoint_url: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_bucket: str = "cv-private"
    s3_access_key: str = "minio-dev"
    s3_secret_key: str = "change-me-local-only"
    s3_use_ssl: bool = False
    presigned_upload_ttl_seconds: int = 300

    ai_routing_mode: str = "local"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    external_ai_enabled: bool = False
    external_ai_base_url: str | None = None
    external_ai_api_key: str | None = None
    external_ai_model: str | None = None
    external_ai_requires_consent: bool = True

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.app_env == "production":
            if (
                self.jwt_secret_key in _DISALLOWED_PROD_SECRETS
                or len(self.jwt_secret_key) < 32
            ):
                raise ValueError(
                    "JWT_SECRET_KEY must be a unique secret of at least 32 characters in production"
                )
            if self.s3_secret_key in _DISALLOWED_PROD_SECRETS:
                raise ValueError("S3_SECRET_KEY must not use a development default in production")
            if any(bad in self.database_url for bad in ("change-me-local-only", "local-admin-only")):
                raise ValueError("DATABASE_URL must not use a development password in production")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def allowed_upload_type_list(self) -> set[str]:
        return {item.strip() for item in self.allowed_upload_types.split(",") if item.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
