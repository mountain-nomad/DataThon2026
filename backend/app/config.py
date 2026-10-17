from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./app.db"  # e.g. postgresql+psycopg://user:pass@db:5432/app
    ml_service_url: str = "http://localhost:8001"
    ml_timeout_seconds: float = 30.0
    cors_origins: list[str] = ["http://localhost:3000"]


settings = Settings()
