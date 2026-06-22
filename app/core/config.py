"""
Модуль конфигурации приложения "Журнал регистрации УТЗ".

Отвечает за загрузку, валидацию и предоставление всех настроек приложения.
Настройки загружаются из переменных окружения и файлов `.env.local`, `.env`
с помощью Pydantic Settings (v2).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import List


class Settings(BaseSettings):
    """
    Основной класс настроек приложения.

    Все параметры можно переопределять через переменные окружения.
    Поддерживает файлы `.env.local` и `.env`. После импорта модуля
    доступен глобальный экземпляр `settings`.
    """

    app_env: str = Field(
        default="dev",
        alias="APP_ENV",
        description="Окружение приложения (dev, test, prod и т.д.)"
    )
    
    database_url: str = Field(
        alias="DATABASE_URL",
        description="URL для подключения к PostgreSQL"
    )
    
    default_ttl_seconds: int = Field(
        default=1800,
        alias="DEFAULT_TTL_SECONDS",
        description="Время жизни по умолчанию для кэша/токенов в секундах"
    )

    # Ключ для валидации JWT (должен совпадать с auth-сервисом)
    SECRET_KEY: str = Field(
        ...,
        alias="SECRET_KEY",
        description="Секретный ключ для подписи и проверки JWT-токенов"
    )
    
    ALGORITHM: str = Field(
        default="HS256",
        description="Алгоритм шифрования JWT"
    )

    # Список пользователей, обладающих правами администратора
    admin_users: List[str] = Field(
        default_factory=lambda: [
            "vgrubtsov", "yuaalekseeva", "lrshlyogin", "pyagavrilov", "mabaturin"
        ],
        description="Список логинов пользователей, имеющих административные права"
    )

    PROJECT_NAME: str = Field(
        default="Журнал регистрации УТЗ",
        description="Название проекта (используется в заголовках, логах, Swagger)"
    )
    
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default_factory=list,
        description="Список разрешённых CORS-ориджинов для backend"
    )

    model_config = SettingsConfigDict(
        env_file=(".env.local", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Глобальный экземпляр настроек (singleton), импортируется в других модулях
settings = Settings()
