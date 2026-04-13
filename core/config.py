from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_host: str = "localhost"
    database_port: int = 5433
    database_user: str = "admin_user_doc"
    database_password: str = "admin_user_doc"
    database_name: str = "doc_persona"
    database_schema: str = "admin_portal_ai"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str = "change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # App
    environment: str = "development"
    log_level: str = "INFO"
    rate_limit_per_minute: int = 60

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql+psycopg2://{self.database_user}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def celery_broker_url(self) -> str:
        return self.redis_url

    @property
    def celery_result_backend(self) -> str:
        return self.redis_url


settings = Settings()
