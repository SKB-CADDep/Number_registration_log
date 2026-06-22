"""
Модуль ORM-модели сессий резервирования номеров.

Содержит модель Session, которая отвечает за временное резервирование 
пула регистрационных номеров за конкретным пользователем и оборудованием.

Обеспечивает безопасную конкурентную работу: пока сессия активна, 
зарезервированные номера заблокированы для других пользователей, 
что предотвращает race condition.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, DateTime, func, Integer, Enum

from app.models.base import Base


class SessionStatus(str, enum.Enum):
    """Статусы жизненного цикла сессии резервирования номеров."""
    active = "active"       # Сессия активна, номера зарезервированы
    cancelled = "cancelled" # Досрочно отменена пользователем
    completed = "completed" # Успешно завершена (документы зарегистрированы)
    expired = "expired"     # Истекло время жизни (TTL), бронь автоматически снята


class Session(Base):
    """
    Модель сессии резервирования регистрационных номеров (таблица 'sessions').

    Используется для массовой регистрации документов. Одна сессия привязывается
    к пользователю и оборудованию и имеет ограниченное время жизни (TTL).
    """

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        doc="Уникальный идентификатор сессии (UUID v4 в виде строки).",
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        doc="ID пользователя, создавшего сессию резервирования.",
    )

    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipment.id", ondelete="RESTRICT"),
        nullable=False,
        doc="ID оборудования, для которого резервируются номера.",
    )

    requested_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Количество номеров, запрошенных пользователем в рамках этой сессии.",
    )

    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status"),
        default=SessionStatus.active,
        doc="Текущий статус сессии.",
    )

    ttl_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Время жизни сессии в секундах (Time To Live).",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="Дата и время создания сессии.",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        doc="Расчётное время истечения сессии (created_at + ttl_seconds). "
            "После этой даты сессия считается просроченной.",
    )
