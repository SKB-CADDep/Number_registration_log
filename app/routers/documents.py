"""
Модуль маршрутизации (API Router) для работы с документами.

Предоставляет эндпоинты для:
- Назначения регистрационных номеров документам
- Резервирования «золотых» номеров (кратных 100)
- Получения информации о документе
- Редактирования метаданных документа администраторами

Реализует сложные бизнес-правила:
- защита «золотых» номеров от обычных пользователей,
- валидацию и контроль сессий резервирования,
- аудит всех административных действий.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.core.db import lifespan_session
from app.core.auth import get_current_user, CurrentUser
from app.services.documents import DocumentsService
from app.services.reservation import ReservationService
from app.schemas.admin import AdminDocumentUpdate
from app.schemas.documents import (
    DocumentAssignOne,
    GoldenNumberReservationRequest,
    GoldenNumberReservationResponse,
)
from app.schemas.responses import AssignNumberOut, CreatedDocumentInfo
from app.utils.numbering import format_doc_no


router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post(
    "/assign-one",
    response_model=AssignNumberOut,
    summary="Назначение одного регистрационного номера",
    description=(
        "Присваивает документу регистрационный номер в рамках активной сессии "
        "резервирования. Защищает «золотые» номера (заканчивающиеся на 00) "
        "от использования обычными пользователями."
    ),
)
async def assign_one(
    payload: DocumentAssignOne,
    session: AsyncSession = Depends(lifespan_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """
    Назначает один регистрационный номер новому документу.

    Выполняет комплексную бизнес-логику:
    - проверяет валидность и принадлежность сессии резервирования,
    - защищает «золотые» номера от обычных пользователей,
    - проверяет уникальность номера,
    - создаёт запись документа и возвращает информацию о нём.

    Args:
        payload: Данные запроса (session_id, doc_name, note, numeric).
        user: Текущий авторизованный пользователь.

    Returns:
        AssignNumberOut: Информация о созданном документе и сопроводительное сообщение.

    Raises:
        HTTPException(400): При ошибках валидации или бизнес-правил.
        HTTPException(403): При попытке обычного пользователя захватить «золотой» номер.
        HTTPException(409): При конфликте (ValueError из сервиса).
    """
    service = DocumentsService(session)
    try:
        result_dict = await service.assign_one(
            session_id=payload.session_id,
            user_id=user.id,
            doc_name=payload.doc_name,
            note=payload.note,
            is_admin=user.is_admin,
            numeric=payload.numeric,
        )

        if result_dict.get("created") is None:
            message = result_dict.get("message", "Не удалось назначить номер.")
            status_code = (
                status.HTTP_403_FORBIDDEN
                if "ХХХХ00" in message
                else status.HTTP_400_BAD_REQUEST
            )

            raise HTTPException(status_code=status_code, detail=message)

        created_info = CreatedDocumentInfo.model_validate(result_dict["created"])
        response_obj = AssignNumberOut(
            created=created_info, message=result_dict["message"]
        )
        return response_obj.model_dump()

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.patch(
    "/{document_id}",
    response_model=dict,
    summary="Редактирование документа (только администратор)",
    description="Изменяет название и/или примечание документа. Доступно исключительно администраторам. Все изменения фиксируются в аудите.",
)
async def edit_document(
    document_id: int,
    data: AdminDocumentUpdate,
    session: AsyncSession = Depends(lifespan_session),
    user: CurrentUser = Depends(get_current_user),
) -> dict:
    """
    Редактирует метаданные существующего документа.

    Требует прав администратора. Все изменения логируются через систему аудита.

    Args:
        document_id: Идентификатор документа.
        data: Новые данные (название, примечание).
        user: Текущий пользователь (должен быть администратором).

    Returns:
        dict: Результат выполнения операции от сервиса.

    Raises:
        HTTPException(403): Если пользователь не является администратором.
        HTTPException(404): Если документ не найден.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Только админ."
        )

    service = DocumentsService(session)
    try:
        result = await service.edit_document_admin(
            document_id=document_id,
            username=user.username,
            data=data,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get(
    "/{document_id}",
    summary="Получение информации о документе",
    description="Возвращает детальную информацию о документе. Доступно только администраторам.",
)
async def get_document(
    document_id: int,
    session: AsyncSession = Depends(lifespan_session),
    user: CurrentUser = Depends(get_current_user),
) -> JSONResponse:
    """
    Возвращает полную информацию о документе по его внутреннему ID.

    Примечание: используется ручное формирование JSONResponse вместо Pydantic-модели
    (оставлено для совместимости/особенностей текущей реализации).

    Args:
        document_id: Внутренний идентификатор документа.
        user: Текущий пользователь (должен быть администратором).

    Returns:
        JSONResponse: Детальная информация о документе, включая отформатированный номер.

    Raises:
        HTTPException(403): Если пользователь не администратор.
        HTTPException(404): Если документ не найден.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Только админ."
        )

    # Локальный импорт оставлен для предотвращения возможных циклических зависимостей
    from app.repositories.documents import DocumentsRepository

    repo = DocumentsRepository(session)
    doc = await repo.get(document_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Документ не найден."
        )

    return JSONResponse(
        {
            "id": doc.id,
            "doc_name": doc.doc_name,
            "note": doc.note,
            "numeric": doc.numeric,
            "formatted_no": format_doc_no(doc.numeric),
            "reg_date": doc.reg_date.isoformat() if doc.reg_date else None,
        }
    )


@router.post(
    "/reserve-golden",
    response_model=GoldenNumberReservationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Резервирование 'золотых' номеров (только администратор)",
    description=(
        "Позволяет администратору зарезервировать указанное количество "
        "'золотых' номеров (заканчивающихся на 00). Используется для особых "
        "случаев (важные контракты, специальные проекты и т.п.)."
    ),
)
async def reserve_golden_numbers(
    payload: GoldenNumberReservationRequest,
    session: AsyncSession = Depends(lifespan_session),
    user: CurrentUser = Depends(get_current_user),
) -> GoldenNumberReservationResponse:
    """
    Резервирует заданное количество свободных «золотых» номеров.

    Доступно **только администраторам**. Создаёт сессию резервирования
    и возвращает список зарезервированных номеров.

    Args:
        payload: Запрос с equipment_id, quantity и ttl_seconds.
        user: Текущий пользователь (должен быть администратором).

    Returns:
        GoldenNumberReservationResponse: session_id и список зарезервированных номеров.

    Raises:
        HTTPException(403): Если пользователь не администратор.
        HTTPException(409): При конфликте (например, недостаточно свободных номеров).
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Эта операция доступна только администраторам.",
        )

    service = ReservationService(session)
    try:
        session_id, reserved_numbers = await service.reserve_golden_numbers(
            user_id=user.id,
            equipment_id=payload.equipment_id,
            quantity=payload.quantity,
            ttl_seconds=payload.ttl_seconds,
        )
        return GoldenNumberReservationResponse(
            session_id=session_id, reserved_numbers=reserved_numbers
        )

    except HTTPException as e:
        raise e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
