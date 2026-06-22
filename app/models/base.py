"""
Модуль базовых классов SQLAlchemy.

Содержит корневой класс `Base` для всех ORM-моделей приложения, 
а также миксины (mixins) с переиспользуемыми полями и поведением.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import func, DateTime


class Base(DeclarativeBase):
    """
    Базовый класс для всех ORM-моделей приложения.

    Использует современный стиль SQLAlchemy 2.0 (DeclarativeBase).
    Является источником метаданных (`metadata`) для Alembic.
    """
    pass


class TimestampMixin:
    """
    Миксин, добавляющий автоматическую метку времени создания записи.

    При наследовании модель получает поле `created_at`, которое заполняется
    на стороне базы данных при вставке новой записи.
    """
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="Дата и время создания записи. Заполняется автоматически на сервере БД.",
    )
