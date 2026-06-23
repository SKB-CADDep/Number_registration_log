"""
Модуль репозитория для работы со справочником оборудования.

Реализует паттерн Repository для управления сущностью Equipment.
Предоставляет методы для создания оборудования, поиска по различным критериям,
выявления дубликатов и получения уникальных значений для автокомплита.
"""

from __future__ import annotations

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.equipment import Equipment


class EquipmentRepository:
    """
    Репозиторий для работы с таблицей `equipment`.

    Содержит логику поиска, создания оборудования, проверки на дубликаты,
    а также получения уникальных значений для автозаполнения на фронтенде.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория."""
        self.session = session

    async def create(self, data: dict) -> Equipment:
        """
        Создаёт новую единицу оборудования.

        Args:
            data: Словарь с данными оборудования.

        Returns:
            Equipment: Созданный объект оборудования.
        """
        equipment = Equipment(**data)
        self.session.add(equipment)
        await self.session.flush()
        return equipment

    async def get(self, id_: int) -> Equipment | None:
        """Возвращает оборудование по его внутреннему ID."""
        result = await self.session.execute(
            select(Equipment).where(Equipment.id == id_)
        )
        return result.scalars().first()

    async def search(
        self,
        station_object: str | None = None,
        station_no: str | None = None,
        label: str | None = None,
        factory_no: str | None = None,
        order_no: str | None = None,
        q: str | None = None,
    ) -> list[Equipment]:
        """
        Выполняет многокритериальный поиск оборудования.

        Поддерживает как фильтрацию по конкретным полям, так и глобальный поиск
        по строке `q` (поиск по всем текстовым полям с использованием ILIKE).

        Returns:
            list[Equipment]: Список найденного оборудования (не более 50 записей).
        """
        stmt = select(Equipment)
        conditions = []

        if station_object:
            conditions.append(Equipment.station_object.ilike(f"%{station_object}%"))
        if station_no:
            conditions.append(Equipment.station_no == station_no)
        if label:
            conditions.append(Equipment.label == label)
        if factory_no:
            conditions.append(Equipment.factory_no == factory_no)
        if order_no:
            conditions.append(Equipment.order_no == order_no)

        # Глобальный поиск по всем основным полям
        if q:
            q_conditions = [
                Equipment.station_object.ilike(f"%{q}%"),
                Equipment.station_no.ilike(f"%{q}%"),
                Equipment.label.ilike(f"%{q}%"),
                Equipment.factory_no.ilike(f"%{q}%"),
                Equipment.order_no.ilike(f"%{q}%"),
            ]
            conditions.append(or_(*q_conditions))

        if conditions:
            stmt = stmt.where(and_(*conditions))

        stmt = stmt.order_by(Equipment.id.desc()).limit(50)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def find_duplicate(
        self,
        station_object: str | None = None,
        station_no: str | None = None,
        label: str | None = None,
        factory_no: str | None = None,
    ) -> Equipment | None:
        """
        Проверяет наличие точного дубликата оборудования перед созданием новой записи.

        Использует строгое сравнение (==), а не ILIKE.
        """
        conditions = []

        if station_object:
            conditions.append(Equipment.station_object == station_object)
        if station_no:
            conditions.append(Equipment.station_no == station_no)
        if label:
            conditions.append(Equipment.label == label)
        if factory_no:
            conditions.append(Equipment.factory_no == factory_no)

        if not conditions:
            return None

        stmt = select(Equipment).where(and_(*conditions)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_all(self, limit: int = 100) -> list[Equipment]:
        """Возвращает все записи оборудования (с ограничением по умолчанию)."""
        result = await self.session.execute(
            select(Equipment).order_by(Equipment.id.desc()).limit(limit)
        )
        return list(result.scalars().all())

    async def list_distinct(
        self,
        field: str,
        q: str | None = None,
        station_object: str | None = None,
    ) -> list[str]:
        """
        Возвращает список уникальных значений указанного поля.

        Используется для реализации автокомплита на фронтенде.

        Args:
            field: Название поля ('station_object', 'label', 'station_no' и т.д.).
            q: Строка для фильтрации (ILIKE).
            station_object: Дополнительный фильтр по объекту подстанции 
                           (используется при выборе номера или маркировки).

        Returns:
            list[str]: Уникальные значения (максимум 20).
        """
        col = getattr(Equipment, field)
        stmt = select(func.distinct(col))

        if q:
            stmt = stmt.where(col.ilike(f"%{q}%"))

        if station_object:
            if field in ("station_no", "label"):
                stmt = stmt.where(Equipment.station_object == station_object)

        result = await self.session.execute(stmt.order_by(col.asc()).limit(20))
        return [row[0] for row in result.fetchall() if row[0] is not None]
