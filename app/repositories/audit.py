"""
Модуль репозитория для работы с журналом аудита.

Реализует паттерн Repository (Data Access Layer). 
Отвечает за сохранение истории изменений документов в таблицу `audit_logs`.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog


class AuditRepository:
    """
    Репозиторий для управления записями аудита (AuditLog).

    Инкапсулирует всю логику сохранения истории изменений документов.
    Следует принципу "одна транзакция — один commit" на уровне сервиса.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализация репозитория.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self.session = session

    async def add(
        self,
        *,
        document_id: int,
        doc_number: int,
        username: str,
        diff: dict,
    ) -> None:
        """
        Создаёт и сохраняет запись в журнал аудита.

        Важно: метод выполняет `flush()`, но **не** делает `commit()`.
        Коммит транзакции должен происходить на уровне сервиса, чтобы
        обеспечить атомарность операции (сохранение документа + запись аудита).

        Args:
            document_id: Идентификатор документа.
            doc_number: Регистрационный номер документа на момент изменения.
            username: Логин пользователя, внёсшего изменения.
            diff: Словарь с изменениями (что было изменено, старые и новые значения).
        """
        audit_log = AuditLog(
            document_id=document_id,
            doc_number=doc_number,
            username=username,
            diff=diff,
        )

        self.session.add(audit_log)
        await self.session.flush()
