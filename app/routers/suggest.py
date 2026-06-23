"""
Модуль маршрутизации (API Router) для системы автодополнения (Suggest/Autocomplete).

Предоставляет эндпоинты для получения уникальных значений из справочников
документов и оборудования. Используется фронтендом для реализации выпадающих
списков, подсказок при вводе и ускорения поиска.

Все эндпоинты публичны (доступны любому авторизованному пользователю)
и возвращают не более 20 результатов для обеспечения производительности.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import lifespan_session
from app.models.document import Document
from app.repositories.equipment import EquipmentRepository


router = APIRouter(prefix="/suggest", tags=["Suggest"])


@router.get(
    "/doc-names",
    response_model=list[str],
    summary="Автодополнение названий документов",
    description=(
        "Возвращает до 20 уникальных названий документов. "
        "Поддерживает частичный поиск (ILIKE). При пустом запросе "
        "возвращает первые 20 названий в алфавитном порядке."
    ),
)
async def suggest_doc_names(
    q: str | None = None,
    session: AsyncSession = Depends(lifespan_session),
) -> list[str]:
    """
    Возвращает список уникальных названий документов для автодополнения.

    Использует `DISTINCT` + `ILIKE` для поиска по подстроке. Результат
    всегда ограничен 20 записями и отсортирован по алфавиту.

    Args:
        q: Поисковая подстрока (необязательно). Если не передана или пуста —
           возвращаются первые 20 названий.
        session: Асинхронная сессия БД.

    Returns:
        list[str]: Уникальные названия документов (максимум 20).
    """
    stmt = select(func.distinct(Document.doc_name))

    if q and q.strip():
        stmt = stmt.where(Document.doc_name.ilike(f"%{q.strip()}%"))

    stmt = stmt.order_by(Document.doc_name.asc()).limit(20)
    result = await session.execute(stmt)

    return [row[0] for row in result.fetchall() if row[0]]


@router.get(
    "/equipment/{field}",
    response_model=list[str],
    summary="Автодополнение полей оборудования",
    description=(
        "Возвращает уникальные значения указанного поля справочника оборудования. "
        "Поддерживает фильтрацию по частичному совпадению и по объекту подстанции."
    ),
)
async def suggest_equipment_field(
    field: str,
    q: str | None = None,
    station_object: str | None = None,
    session: AsyncSession = Depends(lifespan_session),
) -> list[str]:
    """
    Возвращает список уникальных значений для выбранного поля таблицы оборудования.

    Для предотвращения SQL injection и некорректных запросов используется whitelist
    разрешённых полей. Если передано недопустимое поле — возвращается пустой список.

    Args:
        field: Имя поля оборудования (eq_type, factory_no, order_no, label,
               station_no, station_object).
        q: Поисковая подстрока для фильтрации по частичному совпадению.
        station_object: Ограничение поиска по конкретному объекту подстанции.
        session: Асинхронная сессия БД.

    Returns:
        list[str]: Уникальные значения указанного поля (максимум 20).
    """
    repo = EquipmentRepository(session)

    # Защита от передачи произвольных/несуществующих полей в БД
    allowed_fields = {
        "eq_type",
        "factory_no",
        "order_no",
        "label",
        "station_no",
        "station_object",
    }
    if field not in allowed_fields:
        return []

    values = await repo.list_distinct(
        field=field, q=q, station_object=station_object
    )
    return values
