"""
Модуль бизнес-логики работы со справочником оборудования.

Отвечает за создание новых записей оборудования с проверкой уникальности
(по заводскому номеру и комбинации атрибутов), а также предоставляет
методы поиска и получения данных.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.repositories.equipment import EquipmentRepository
from app.models.equipment import Equipment


class EquipmentService:
    """
    Сервис для управления справочником оборудования.

    Выполняет бизнес-правила при создании записей:
    - проверка уникальности заводского номера (`factory_no`);
    - (закомментирована) расширенная проверка на дублирование по комбинации
      станция + станционный номер + маркировка + заводской номер.

    Использует `EquipmentRepository` для выполнения запросов к базе данных.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация сервиса с репозиторием оборудования."""
        self.session = session
        self.repo = EquipmentRepository(session)

    async def create(self, data: dict) -> Equipment:
        """
        Создаёт новую запись оборудования с проверкой уникальности.

        Проверяет наличие оборудования с таким же заводским номером (`factory_no`).
        При обнаружении дубликата выбрасывает HTTP 409 Conflict.

        Примечание: вызов `_check_duplicates()` сейчас закомментирован.
        При необходимости включения расширенной проверки на дубликаты
        по комбинации полей — раскомментируйте строку.

        Args:
            data: Словарь с данными оборудования (eq_type, factory_no, order_no и т.д.).

        Returns:
            Equipment: Созданная ORM-модель оборудования.

        Raises:
            HTTPException(409): Если оборудование с таким заводским номером
                                или комбинацией атрибутов уже существует.
        """
        factory_no = data.get("factory_no")

        # Проверяем на дубликат только если factory_no передан
        if factory_no:
            query = select(Equipment).where(Equipment.factory_no == factory_no)
            result = await self.session.execute(query)
            existing_equipment = result.scalars().first()

            if existing_equipment:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Оборудование с заводским номером '{factory_no}' уже существует.",
                )

        try:
            # await self._check_duplicates(data)   # закомментировано
            eq = await self.repo.create(data)
            await self.session.commit()
            await self.session.refresh(eq)
            return eq

        except IntegrityError:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Объект с такими атрибутами уже существует.",
            )

    async def get(self, id_: int) -> Equipment | None:
        """
        Возвращает оборудование по его внутреннему ID.

        Args:
            id_: Идентификатор оборудования.

        Returns:
            Equipment | None: Найденная запись или None.
        """
        return await self.repo.get(id_)

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

        Поддерживает фильтрацию по отдельным полям и глобальный поиск (`q`).

        Args:
            station_object: Объект подстанции.
            station_no: Станционный номер.
            label: Маркировка оборудования.
            factory_no: Заводской номер.
            order_no: Номер заказа.
            q: Глобальный поиск по всем полям.

        Returns:
            list[Equipment]: Список найденных записей оборудования.
        """
        return await self.repo.search(
            station_object=station_object,
            station_no=station_no,
            label=label,
            factory_no=factory_no,
            order_no=order_no,
            q=q,
        )

    async def _check_duplicates(self, data: dict) -> None:
        """
        Проверяет наличие дублирующей записи оборудования по комбинации полей.

        Метод не используется в текущей реализации `create()` (вызов закомментирован).
        Оставлен для возможного будущего расширения бизнес-правил.

        Если все ключевые поля пустые — дубликатов быть не может.
        """
        if not any([
            data.get("station_object"),
            data.get("station_no"),
            data.get("label"),
            data.get("factory_no"),
        ]):
            return

        duplicate = await self.repo.find_duplicate(
            station_object=data.get("station_object"),
            station_no=data.get("station_no"),
            label=data.get("label"),
            factory_no=data.get("factory_no"),
        )

        if duplicate:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Объект с такими атрибутами уже существует.",
            )

    async def get_all(self, limit: int = 100) -> list[Equipment]:
        """
        Возвращает все записи оборудования с ограничением по количеству.

        Используется в основном для административных задач и отладки.

        Args:
            limit: Максимальное количество возвращаемых записей.

        Returns:
            list[Equipment]: Список оборудования.
        """
        return await self.repo.get_all(limit=limit)
