from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg2://atc:atc_dev@db:5432/atc"
    environment: str = "development"

    # JWT Configuration
    jwt_secret_key: str = "CHANGE_THIS_SECRET_IN_PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_issuer: str | None = None
    jwt_audience: str | None = None


settings = Settings()
