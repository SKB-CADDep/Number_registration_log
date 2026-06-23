"""
Модуль маршрутизации (API Router) для управления сессиями резервирования номеров.

Предоставляет эндпоинты для:
- Создания новой сессии и первоначального резервирования пакета номеров
- Добавления дополнительных номеров в активную сессию
- Получения статуса и списка зарезервированных номеров
- Завершения сессии (как успешного, так и досрочного) с освобождением неиспользованных номеров

Сессии используются для временной блокировки номеров за пользователем и оборудованием,
предотвращая race condition при массовой регистрации документов.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.core.auth import get_current_user, CurrentUser
from app.core.config import settings
from app.core.db import lifespan_session
from app.repositories.doc_numbers import DocNumbersRepository
from app.repositories.sessions import SessionsRepository
from app.schemas.sessions import SessionStart, ReserveResult, AddNumbers
from app.services.reservation import ReservationService


router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post(
    "/reserve",
    response_model=ReserveResult,
    summary="Старт сессии и резервирование номеров",
    description=(
        "Создает новую сессию резервирования и блокирует запрошенное количество "
        "свободных регистрационных номеров за пользователем и оборудованием."
    ),
)
async def start_session_and_reserve(
    payload: SessionStart,
    session: AsyncSession = Depends(lifespan_session),
    user: CurrentUser = Depends(get_current_user),
) -> ReserveResult:
    """
    Инициализирует сессию массовой регистрации документов и резервирует пакет номеров.

    Использует `ReservationService` для атомарного создания сессии и захвата номеров.
    Если `ttl_seconds` не передан, используется значение по умолчанию из настроек.

    Args:
        payload: Данные для создания сессии (equipment_id, requested_count, ttl_seconds).
        user: Текущий авторизованный пользователь.
        session: Асинхронная сессия БД.

    Returns:
        ReserveResult: Идентификатор сессии и список зарезервированных номеров.
    """
    service = ReservationService(session)
    ttl = payload.ttl_seconds or settings.default_ttl_seconds

    session_id, reserved_numbers = await service.start_session(
        user_id=user.id,
        equipment_id=payload.equipment_id,
        requested_count=payload.requested_count,
        ttl_seconds=ttl,
    )
    return ReserveResult(session_id=session_id, reserved_numbers=reserved_numbers)


@router.post(
    "/{session_id}/complete",
    response_model=dict,
    summary="Завершение сессии",
    description=(
        "Завершает сессию (успешно или досрочно). Освобождает все зарезервированные, "
        "но не использованные номера, возвращая их в общий пул."
    ),
)
async def complete_session(
    session_id: str,
    session: AsyncSession = Depends(lifespan_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """
    Завершает сессию резервирования и освобождает неиспользованные номера.

    Вызывается при успешном завершении регистрации документов или при отмене
    пользователем. Выполняет `commit()` самостоятельно.

    Args:
        session_id: UUID активной сессии.
        user: Текущий авторизованный пользователь.
        session: Асинхронная сессия БД.

    Returns:
        dict: Статус операции, сообщение и количество освобождённых номеров.

    Raises:
        HTTPException: При ошибках работы с репозиториями (будут обработаны выше).
    """
    numbers_repo = DocNumbersRepository(session)
    sessions_repo = SessionsRepository(session)

    released_count = await numbers_repo.release_session(session_id)

    await sessions_repo.set_status(session_id, "completed")
    await session.commit()

    return {
        "success": True,
        "message": "Сессия завершена",
        "released_count": released_count,
    }


@router.get(
    "/{session_id}",
    summary="Получение статуса сессии",
    description="Возвращает полную информацию о сессии резервирования.",
)
async def get_session(
    session_id: str,
    session: AsyncSession = Depends(lifespan_session),
    user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """
    Возвращает актуальное состояние сессии резервирования.

    Args:
        session_id: UUID сессии.
        user: Текущий авторизованный пользователь.
        session: Асинхронная сессия БД.

    Returns:
        JSONResponse: Метаданные сессии (id, user_id, equipment_id, статус, сроки жизни и т.д.).

    Raises:
        HTTPException(404): Если сессия не найдена.
    """
    repo = SessionsRepository(session)
    session_obj = await repo.get(session_id)

    if not session_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Сессия не найдена",
        )

    return JSONResponse(
        {
            "id": session_obj.id,
            "user_id": session_obj.user_id,
            "equipment_id": session_obj.equipment_id,
            "requested_count": session_obj.requested_count,
            "status": session_obj.status.value,
            "ttl_seconds": session_obj.ttl_seconds,
            "created_at": session_obj.created_at.isoformat(),
            "expires_at": session_obj.expires_at.isoformat(),
        }
    )


@router.get(
    "/{session_id}/reserved",
    summary="Просмотр зарезервированных номеров",
    description="Возвращает список всех номеров, удерживаемых текущей сессией, с форматированием для frontend.",
)
async def get_reserved_numbers(
    session_id: str,
    session: AsyncSession = Depends(lifespan_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """
    Возвращает список номеров, зарезервированных в рамках указанной сессии.

    Включает признак «золотого» номера и отформатированное представление
    (например «УТЗ-000100»).

    Args:
        session_id: UUID сессии.
        user: Текущий авторизованный пользователь.
        session: Асинхронная сессия БД.

    Returns:
        dict: Список зарезервированных номеров с дополнительной информацией.
    """
    numbers_repo = DocNumbersRepository(session)
    reserved = await numbers_repo.get_reserved_for_session(session_id)

    if not reserved:
        return {"reserved": [], "message": "Нет зарезервированных номеров"}

    # Форматируем номера для отображения
    formatted_numbers = []
    for num in reserved:
        formatted_numbers.append({
            "numeric": num.numeric,
            "is_golden": num.is_golden,
            "formatted": f"УТЗ-{num.numeric:06d}",
        })

    return {"reserved": formatted_numbers, "count": len(formatted_numbers)}


@router.post(
    "/{session_id}/add-numbers",
    response_model=list[int],
    summary="Добавление номеров в сессию",
    description=(
        "Позволяет дозаказать дополнительные номера (включая золотые) "
        "в уже существующую активную сессию."
    ),
)
async def add_numbers(
    session_id: str,
    payload: AddNumbers,
    session: AsyncSession = Depends(lifespan_session),
    user: CurrentUser = Depends(get_current_user),
) -> list[int]:
    """
    Расширяет существующую сессию дополнительными номерами.

    Поддерживает как обычные, так и «золотые» номера. Для золотых номеров
    выполняется проверка прав (обычные пользователи не могут их резервировать напрямую).

    Args:
        session_id: UUID существующей сессии.
        payload: Запрос с количеством и/или конкретными номерами.
        user: Текущий пользователь (используется для проверки прав администратора).
        session: Асинхронная сессия БД.

    Returns:
        list[int]: Список числовых значений успешно добавленных номеров.

    Raises:
        HTTPException(404): Если сессия не найдена или уже завершена (ValueError из сервиса).
        HTTPException(403): При попытке нарушения правил резервирования золотых номеров.
    """
    service = ReservationService(session)
    try:
        new_numbers = await service.add_numbers_to_session(
            session_id=session_id,
            user_id=user.id,
            requested_count=payload.requested_count,
            numbers=payload.numbers,
            quantity_golden=payload.quantity_golden,
            is_admin=user.is_admin,
        )
        return new_numbers
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
