"""
Модуль ORM-модели зарегистрированных документов.

Основная модель приложения. Хранит информацию о зарегистрированных 
документах, их названиях, примечаниях и привязке к оборудованию.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, func, Index
from sqlalchemy.dialects.postgresql import CITEXT

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.equipment import Equipment


class Document(Base, TimestampMixin):
    """
    Модель зарегистрированного документа (таблица 'documents').
    """

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        doc="Уникальный идентификатор документа.",
    )

    numeric: Mapped[int] = mapped_column(
        unique=True,
        nullable=False,
        doc="Регистрационный номер документа.",
    )

    reg_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="Дата и время регистрации документа.",
    )

    doc_name: Mapped[str] = mapped_column(
        CITEXT,
        nullable=False,
        doc="Название документа (case-insensitive).",
    )

    note: Mapped[str | None] = mapped_column(
        CITEXT,
        nullable=True,
        doc="Примечание к документу (case-insensitive).",
    )

    equipment_id: Mapped[int] = mapped_column(
        ForeignKey("equipment.id", ondelete="RESTRICT"),
        nullable=False,
        doc="ID оборудования, к которому относится документ.",
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        doc="ID пользователя, зарегистрировавшего документ.",
    )

    # Relationships
    equipment: Mapped["Equipment"] = relationship(
        "Equipment",
        back_populates="documents",
        lazy="joined",
    )


# Уникальный индекс, защищающий от дублирования одинаковых документов
Index(
    "ix_documents_unique_name_note_equipment",
    Document.doc_name,
    Document.equipment_id,
    func.coalesce(Document.note, ""),
    unique=True,
)
