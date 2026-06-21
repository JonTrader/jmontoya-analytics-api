from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://analytics:analytics@localhost:5432/analytics"
    analytics_api_key: str = "dev-key-change-in-production"
    cors_origins: str = "*"
    debug: bool = False


settings = Settings()
