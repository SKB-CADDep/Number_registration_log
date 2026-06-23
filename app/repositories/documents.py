"""
Модуль репозитория для работы с зарегистрированными документами.

Реализует паттерн Repository для управления сущностью Document.
Отвечает за создание новых документов и их получение с поддержкой 
жадной загрузки (eager loading) связанных сущностей.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document


class DocumentsRepository:
    """
    Репозиторий для работы с таблицей `documents`.

    Инкапсулирует логику создания и чтения документов, а также 
    управление связанными сущностями (оборудование).
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализация репозитория.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self.session = session

    async def create(self, data: dict) -> Document:
        """
        Создаёт новый документ в базе данных.

        Выполняет `flush()`, чтобы получить сгенерированный ID и 
        сделать объект доступным для дальнейшей работы в текущей транзакции.
        Финальный `commit` должен выполняться на уровне сервиса.

        Args:
            data: Словарь с данными документа (соответствует полям модели Document).

        Returns:
            Document: Созданный объект документа.
        """
        document = Document(**data)
        self.session.add(document)
        await self.session.flush()
        return document

    async def get_by_numeric(self, numeric: int) -> Document | None:
        """
        Возвращает документ по его регистрационному номеру.

        Args:
            numeric: Регистрационный номер документа.

        Returns:
            Document | None: Найденный документ или None.
        """
        result = await self.session.execute(
            select(Document).where(Document.numeric == numeric)
        )
        return result.scalars().first()

    async def get(self, id_: int) -> Document | None:
        """
        Возвращает документ по внутреннему ID с жадной загрузкой связанного оборудования.

        Использует `selectinload`, чтобы избежать проблемы N+1 запросов при 
        обращении к `document.equipment` в асинхронном контексте.

        Args:
            id_: Внутренний идентификатор документа.

        Returns:
            Document | None: Документ с подгруженным оборудованием или None.
        """
        stmt = (
            select(Document)
            .where(Document.id == id_)
            .options(selectinload(Document.equipment))
        )

        result = await self.session.execute(stmt)
        return result.scalars().first()
