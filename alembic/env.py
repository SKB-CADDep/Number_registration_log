"""
Alembic конфигурация (env.py).

Этот файл используется Alembic для выполнения миграций базы данных.
Он настраивает подключение к PostgreSQL, определяет метаданные моделей
и обеспечивает корректную работу как в онлайн, так и в оффлайн режиме.

Важные особенности:
- Автоматически преобразует асинхронный URL (`postgresql+asyncpg`) в синхронный
  (`postgresql+psycopg2`), так как Alembic работает в синхронном контексте.
- Импортирует все модели приложения, чтобы Alembic мог отслеживать изменения
  в структуре БД.
"""

from __future__ import annotations

import logging.config
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from app.core.config import settings
from app.models.base import Base

# Импортируем все модели, чтобы Alembic видел все таблицы
from app.models import (  # noqa: F401
    user,
    equipment,
    counter,
    session,
    doc_number,
    document,
    audit,
)

# ====================== Конфигурация ======================

config = context.config

# Настраиваем логирование из alembic.ini (если указан)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ====================== Настройка URL базы данных ======================

if not config.get_main_option("sqlalchemy.url"):
    """
    Если в alembic.ini не указан sqlalchemy.url, берём его из настроек приложения.
    Заменяем async-драйвер на синхронный, так как Alembic не поддерживает
    асинхронные соединения в стандартном режиме.
    """
    if settings.database_url:
        sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
        config.set_main_option("sqlalchemy.url", sync_url)
    else:
        raise RuntimeError("DATABASE_URL не найден ни в alembic.ini, ни в настройках приложения.")


target_metadata = Base.metadata


# ====================== Миграции ======================

def run_migrations_offline() -> None:
    """
    Запуск миграций в offline-режиме.

    В этом режиме Alembic не подключается к реальной базе данных,
    а только генерирует SQL-скрипты.
    """
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Запуск миграций в online-режиме (реальное подключение к БД).

    Используется при выполнении команд `alembic upgrade`, `alembic downgrade`
    и при автогенерации миграций (`--autogenerate`).
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,          # Не используем пул в миграциях
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
