from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    app_env: str = Field(default="dev", alias="APP_ENV")
    database_url: str = Field(alias="DATABASE_URL")
    default_ttl_seconds: int = Field(default=1800, alias="DEFAULT_TTL_SECONDS")

    # Ключ для валидации JWT (совпадает с auth-service)
    SECRET_KEY: str = Field(..., alias="SECRET_KEY")
    ALGORITHM: str = "HS256"

    # Список администраторов удален, так как используется RBAC в БД
    # admin_users: List[str] = [...] 

    PROJECT_NAME: str = "Журнал регистрации УТЗ"
    BACKEND_CORS_ORIGINS: List[str] = []

    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()