"""
Модуль маршрутизации (API Router) для работы со справочником оборудования.

Предоставляет эндпоинты для поиска оборудования по различным критериям
(включая глобальный поиск) и создания новых записей в справочнике.

Поиск доступен всем авторизованным пользователям.
Создание оборудования доступно только администраторам.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.auth import get_current_user, get_current_admin_user, CurrentUser
from app.core.db import lifespan_session
from app.schemas.equipment import EquipmentCreate, EquipmentOut
from app.services.equipment import EquipmentService


router = APIRouter(prefix="/equipment", tags=["Equipment"])


def clean_param(p: str | None) -> str | None:
    """
    Очищает строковый параметр запроса от лишних пробелов.

    Если после очистки строка становится пустой, возвращает None.
    Это предотвращает лишние запросы в базу с пустыми строками.

    Используется во всех фильтрах поиска оборудования.
    """
    if p is None:
        return None
    stripped = p.strip()
    return stripped if stripped else None


@router.get(
    "/search",
    response_model=List[EquipmentOut],
    summary="Поиск оборудования",
    description=(
        "Выполняет многокритериальный поиск по справочнику оборудования. "
        "Поддерживает частичное совпадение по любому из полей, а также "
        "глобальный поиск по всем полям одновременно."
    ),
)
async def search_equipment(
    station_object: str | None = Query(None, description="Объект подстанции"),
    station_no: str | None = Query(None, description="Номер подстанции"),
    label: str | None = Query(None, description="Маркировка/условное обозначение"),
    factory_no: str | None = Query(None, description="Заводской номер"),
    order_no: str | None = Query(None, description="Номер заказа"),
    q: str | None = Query(None, description="Глобальный поиск по всем полям"),
    session: AsyncSession = Depends(lifespan_session),
    user: CurrentUser = Depends(get_current_user),
) -> List[EquipmentOut]:
    """
    Выполняет поиск оборудования по одному или нескольким критериям.

    Все входные параметры очищаются от лишних пробелов через `clean_param()`.
    Доступен всем авторизованным пользователям.

    Args:
        station_object: Название объекта подстанции.
        station_no: Номер подстанции.
        label: Маркировка/условное обозначение оборудования.
        factory_no: Заводской номер.
        order_no: Номер заказа.
        q: Глобальный поиск по всем полям.
        session: Асинхронная сессия БД.
        user: Текущий авторизованный пользователь.

    Returns:
        List[EquipmentOut]: Список найденных единиц оборудования.
    """
    service = EquipmentService(session)
    results = await service.search(
        station_object=clean_param(station_object),
        station_no=clean_param(station_no),
        label=clean_param(label),
        factory_no=clean_param(factory_no),
        order_no=clean_param(order_no),
        q=clean_param(q),
    )
    return results


@router.post(
    "",
    response_model=EquipmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Создание оборудования (только администратор)",
    description=(
        "Добавляет новую запись оборудования в справочник. "
        "Доступно исключительно администраторам. "
        "Выполняет проверку на дубликаты по заводскому номеру и другим ключевым полям."
    ),
)
async def create_equipment(
    eq_in: EquipmentCreate,
    session: AsyncSession = Depends(lifespan_session),
    _admin_user: CurrentUser = Depends(get_current_admin_user),
) -> EquipmentOut:
    """
    Создаёт новую запись оборудования в справочнике.

    Защищено зависимостью `get_current_admin_user` — гарантирует,
    что операцию может выполнить только пользователь с правами администратора.

    Args:
        eq_in: Данные для создания оборудования.
        session: Асинхронная сессия БД.
        _admin_user: Используется только для проверки прав (значение не используется).

    Returns:
        EquipmentOut: Созданная запись оборудования.

    Raises:
        HTTPException(400/409): При нарушении бизнес-правил (дубликат заводского номера и т.п.).
        HTTPException(500): При непредвиденных ошибках на уровне БД или сервиса.
    """
    try:
        service = EquipmentService(session)
        equipment = await service.create(eq_in.model_dump())
        return equipment
    except HTTPException as e:
        # Пробрасываем бизнес-ошибки, выброшенные на уровне сервиса
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Внутренняя ошибка сервера: {str(e)}",
        )
