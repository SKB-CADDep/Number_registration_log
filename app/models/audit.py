"""
Модуль ORM-модели аудита (журнала изменений).

Содержит модель AuditLog, предназначенную для ведения истории изменений 
регистрационных документов. Сохраняет информацию о том, кто, когда и какие 
именно изменения (diff) были внесены в документ.
"""

from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB

from app.models.base import Base


class AuditLog(Base):
    """
    Модель журнала аудита изменений документов.

    Хранит историю всех изменений регистрационных данных.
    Используется для отслеживания кто, когда и что именно менял в документе.
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        doc="Уникальный идентификатор записи в журнале аудита.",
    )

    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"),
        doc="ID документа. При удалении документа вся история также удаляется (CASCADE).",
    )

    doc_number: Mapped[int] = mapped_column(
        doc="Регистрационный номер документа на момент внесения изменения.",
    )

    changed_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="Дата и время внесения изменения (по серверному времени).",
    )

    username: Mapped[str] = mapped_column(
        doc="Имя пользователя (логин), выполнившего изменение. Берётся из JWT-токена.",
    )

    diff: Mapped[dict] = mapped_column(
        JSONB,
        doc="JSONB с изменениями. Содержит разницу между предыдущим и новым состоянием "
            "полей документа (что было изменено, старые и новые значения).",
    )
