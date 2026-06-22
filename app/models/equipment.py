"""
Модуль ORM-модели оборудования.

Содержит модель Equipment, представляющую единицу оборудования/техники.
Каждое оборудование может иметь множество связанных документов (регистраций).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, UniqueConstraint
from sqlalchemy.dialects.postgresql import CITEXT

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.document import Document


class Equipment(Base, TimestampMixin):
    """
    Модель оборудования (таблица 'equipment').

    Хранит основную информацию об оборудовании и используется как справочник
    при регистрации документов.
    """

    __tablename__ = "equipment"
    __table_args__ = (
        UniqueConstraint("factory_no", name="uq_equipment_factory_no"),
    )

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        doc="Уникальный идентификатор оборудования.",
    )

    eq_type: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        doc="Тип оборудования (например: 'Трансформатор', 'Выключатель' и т.д.).",
    )

    factory_no: Mapped[str | None] = mapped_column(
        CITEXT,
        unique=True,
        index=True,
        doc="Заводской номер оборудования (уникальное поле).",
    )

    order_no: Mapped[str | None] = mapped_column(
        CITEXT,
        doc="Номер заказа/договора.",
    )

    label: Mapped[str | None] = mapped_column(
        CITEXT,
        doc="Условное обозначение/маркировка оборудования.",
    )

    station_no: Mapped[str | None] = mapped_column(
        CITEXT,
        doc="Номер подстанции.",
    )

    station_object: Mapped[str | None] = mapped_column(
        CITEXT,
        doc="Наименование объекта подстанции.",
    )

    notes: Mapped[str | None] = mapped_column(
        String(500),
        doc="Дополнительные примечания по оборудованию.",
    )

    # Relationship
    documents: Mapped[list["Document"]] = relationship(
        back_populates="equipment",
        doc="Список документов, зарегистрированных на данное оборудование.",
    )
