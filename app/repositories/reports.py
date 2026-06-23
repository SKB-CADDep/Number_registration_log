"""
Модуль репозитория для генерации отчетов.

Реализует паттерн Repository для сложных аналитических запросов.
Выполняет JOIN между таблицами Document, Equipment и User и возвращает 
плоские структуры (SQLAlchemy Row), удобные для выгрузки в Excel 
и отображения в таблицах на фронтенде.
"""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import select, and_, or_
from sqlalchemy.engine.row import Row
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.equipment import Equipment
from app.models.user import User


class ReportsRepository:
    """
    Репозиторий для построения аналитических отчётов.

    Содержит оптимизированные запросы с JOIN'ами для получения готовых 
    плоских структур данных. Используется для обычных отчётов, расширенной 
    фильтрации и административных дашбордов.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория."""
        self.session = session

    async def fetch(
        self,
        station_objects: list[str] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> Sequence[Row]:
        """
        Базовый отчёт по зарегистрированным документам.

        Возвращает основные поля с сортировкой от старых документов к новым.
        Используется для стандартной выгрузки в Excel.
        """
        stmt = (
            select(
                Document.numeric,
                Document.reg_date,
                Document.doc_name,
                Document.note,
                Equipment.eq_type,
                Equipment.factory_no,
                Equipment.order_no,
                Equipment.label,
                Equipment.station_no,
                Equipment.station_object,
                User.last_name,
                User.first_name,
                User.middle_name,
                User.department,
                User.username,
            )
            .join(Equipment, Equipment.id == Document.equipment_id)
            .join(User, User.id == Document.user_id)
        )

        where = []
        if station_objects:
            where.append(Equipment.station_object.in_(station_objects))
        if date_from:
            where.append(Document.reg_date >= date_from)
        if date_to:
            where.append(Document.reg_date <= date_to)

        if where:
            stmt = stmt.where(and_(*where))

        stmt = stmt.order_by(Document.reg_date.asc(), Document.numeric.asc())

        result = await self.session.execute(stmt)
        return result.fetchall()

    async def fetch_extended(
        self,
        station_objects: list[str] | None = None,
        station_no: str | None = None,
        label: str | None = None,
        factory_no: str | None = None,
        order_no: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        doc_name: str | None = None,
        username: str | None = None,
        department: str | None = None,
    ) -> Sequence[Row]:
        """
        Расширенный отчёт с гибкой фильтрацией.

        Поддерживает частичный поиск (ILIKE) по большинству текстовых полей.
        Используется для дашбордов и продвинутого поиска на фронтенде.
        Сортировка — от новых документов к старым.
        """
        stmt = (
            select(
                Document.numeric,
                Document.reg_date,
                Document.doc_name,
                Document.note,
                Equipment.eq_type,
                Equipment.factory_no,
                Equipment.order_no,
                Equipment.label,
                Equipment.station_no,
                Equipment.station_object,
                User.username,
                User.department,
            )
            .join(Equipment, Equipment.id == Document.equipment_id)
            .join(User, User.id == Document.user_id)
        )

        where = []

        if station_objects:
            where.append(
                or_(
                    *[
                        Equipment.station_object.ilike(f"%{so}%")
                        for so in station_objects
                    ]
                )
            )
        if station_no:
            where.append(Equipment.station_no == station_no)
        if label:
            where.append(Equipment.label.ilike(f"%{label}%"))
        if factory_no:
            where.append(Equipment.factory_no == factory_no)
        if order_no:
            where.append(Equipment.order_no.ilike(f"%{order_no}%"))
        if doc_name:
            where.append(Document.doc_name.ilike(f"%{doc_name}%"))
        if username:
            where.append(User.username.ilike(f"%{username}%"))
        if department:
            where.append(User.department == department)
        if date_from:
            where.append(Document.reg_date >= date_from)
        if date_to:
            where.append(Document.reg_date <= date_to)

        if where:
            stmt = stmt.where(and_(*where))

        stmt = stmt.order_by(Document.reg_date.desc(), Document.numeric.desc())

        result = await self.session.execute(stmt)
        return result.fetchall()

    async def fetch_extended_admin(
        self,
        station_objects: list[str] | None = None,
        station_no: str | None = None,
        label: str | None = None,
        factory_no: str | None = None,
        order_no: str | None = None,
        username: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        eq_type: str | None = None,
        doc_name: str | None = None,
    ) -> Sequence[Row]:
        """
        Расширенный административный отчёт.

        В отличие от `fetch_extended`, дополнительно возвращает системные 
        идентификаторы (`Document.id`, `Equipment.id`), необходимые для 
        редактирования записей в административной панели.
        """
        stmt = (
            select(
                Document.id,
                Document.numeric,
                Document.reg_date,
                Document.doc_name,
                Document.note,
                Equipment.id.label("eq_id"),
                Equipment.eq_type,
                Equipment.factory_no,
                Equipment.order_no,
                Equipment.label,
                Equipment.station_no,
                Equipment.station_object,
                User.username,
            )
            .join(Equipment, Equipment.id == Document.equipment_id)
            .join(User, User.id == Document.user_id)
        )

        where = []

        if station_objects:
            where.append(
                or_(
                    *[
                        Equipment.station_object.ilike(f"%{so}%")
                        for so in station_objects
                    ]
                )
            )
        if station_no:
            where.append(Equipment.station_no == station_no)
        if label:
            where.append(Equipment.label.ilike(f"%{label}%"))
        if factory_no:
            where.append(Equipment.factory_no == factory_no)
        if order_no:
            where.append(Equipment.order_no.ilike(f"%{order_no}%"))
        if username:
            where.append(User.username.ilike(f"%{username}%"))
        if doc_name:
            where.append(Document.doc_name.ilike(f"%{doc_name}%"))
        if date_from:
            where.append(Document.reg_date >= date_from)
        if date_to:
            where.append(Document.reg_date <= date_to)
        if eq_type:
            where.append(Equipment.eq_type == eq_type)

        if where:
            stmt = stmt.where(and_(*where))

        stmt = stmt.order_by(Document.reg_date.desc(), Document.numeric.desc())

        result = await self.session.execute(stmt)
        return result.fetchall()

    async def get_all_departments(self) -> list[str]:
        """
        Возвращает список всех уникальных отделов пользователей.

        Используется для формирования фильтров и выпадающих списков на фронтенде.
        """
        stmt = (
            select(User.department)
            .where(User.department.is_not(None))
            .distinct()
            .order_by(User.department)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
