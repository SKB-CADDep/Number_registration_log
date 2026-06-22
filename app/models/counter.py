"""
Модуль ORM-модели глобального счетчика документов.

Содержит модель DocCounter, которая отвечает за потокобезопасную 
сквозную нумерацию регистрационных документов. 

Модель гарантирует атомарность инкремента даже при одновременных 
запросах от нескольких пользователей (рекомендуется использовать 
SELECT FOR UPDATE при работе со счетчиком).
"""

from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, DateTime, func

from app.models.base import Base


class DocCounter(Base):
    """
    Модель глобального (singleton) счетчика документов.

    В таблице обычно находится только одна запись. 
    Используется для генерации уникальных регистрационных номеров.
    """

    __tablename__ = "doc_counter"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        doc="Идентификатор записи. Почти всегда равен 1.",
    )

    base_start: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=1,
        doc="Базовое значение, от которого начинается нумерация при сбросе счетчика.",
    )

    next_normal_start: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=1,
        doc="Номер, который будет присвоен следующему зарегистрированному документу. "
            "Увеличивается при каждой успешной регистрации.",
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        doc="Дата и время последнего обновления счетчика. Автоматически обновляется "
            "при каждом изменении записи.",
    )
