from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://atc:atc_dev@db:5432/atc"
    environment: str = "development"

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_issuer: str | None = None
    jwt_audience: str | None = None

    # GitHub OAuth settings
    github_client_id: str | None = None
    github_client_secret: str | None = None
    github_redirect_uri: str | None = None

    # Git worktree settings
    worktrees_base_path: Path = Path("/var/lib/atc/worktrees")

    # File upload settings
    uploads_base_path: Path = Path("/var/lib/atc/uploads")
    max_image_size_bytes: int = 10 * 1024 * 1024  # 10 MB
    allowed_image_types: list[str] = ["image/png", "image/jpeg", "image/gif", "image/webp"]

    # Anthropic API settings
    anthropic_api_key: str | None = None

    # Redis settings for task queue
    redis_url: str = "redis://localhost:6379"

    # Task queue settings
    task_queue_max_retries: int = 3
    task_queue_retry_delay_seconds: int = 60
    task_queue_job_timeout_seconds: int = 600  # 10 minutes for Claude API calls


settings = Settings()
