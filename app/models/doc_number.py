"""
Модуль ORM-модели регистрационных номеров документов.

Содержит модель DocNumber для хранения и управления состоянием каждого 
регистрационного номера, а также перечисление DocNumStatus с возможными 
состояниями номера.
"""

from __future__ import annotations

import enum

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, ForeignKey, DateTime, func, Enum, Boolean

from app.models.base import Base


class DocNumStatus(str, enum.Enum):
    """
    Статусы регистрационных номеров документов.
    """
    reserved = "reserved"   # Номер зарезервирован, но ещё не присвоен
    assigned = "assigned"   # Номер успешно присвоен документу
    released = "released"   # Номер был освобождён (например, документ удалён)


class DocNumber(Base):
    """
    Модель регистрационных номеров документов (таблица 'doc_numbers').

    Хранит каждое числовое значение номера, его статус, информацию о резервировании,
    присвоении и сроке действия резерва. Поддерживает концепцию "золотых" номеров.
    """

    __tablename__ = "doc_numbers"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        doc="Уникальный идентификатор записи в таблице.",
    )

    numeric: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        unique=True,
        doc="Само числовое значение регистрационного номера (уникально).",
    )

    is_golden: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        doc="Признак 'золотого' номера (особо красивый/значимый номер).",
    )

    status: Mapped[DocNumStatus] = mapped_column(
        Enum(DocNumStatus, name="docnum_status"),
        nullable=False,
        doc="Текущий статус номера: reserved, assigned или released.",
    )

    reserved_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        doc="ID пользователя, зарезервировавшего номер.",
    )

    session_id: Mapped[str | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"),
        doc="ID сессии, в рамках которой был зарезервирован номер.",
    )

    reserved_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="Дата и время резервирования номера.",
    )

    assigned_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Дата и время, когда номер был окончательно присвоен документу.",
    )

    released_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Дата и время, когда номер был освобождён (например, при удалении документа).",
    )

    expires_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="Дата и время, после которого резерв на номер автоматически снимается.",
    )
