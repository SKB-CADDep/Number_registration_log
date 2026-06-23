"""
Модуль маршрутизации (API Router) для генерации отчетов и выгрузок.

Предоставляет эндпоинты для получения отфильтрованных данных в формате JSON
(для таблиц и дашбордов) и выгрузки результатов в Excel (.xlsx).

Поддерживает сложную многокритериальную фильтрацию по оборудованию, датам,
пользователям и отделам. Также включает административный поиск документов
для последующего редактирования.
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.background import BackgroundTask
from starlette.responses import FileResponse

from app.core.auth import get_current_user, CurrentUser
from app.core.db import lifespan_session
from app.schemas.admin import AdminDocumentRow
from app.schemas.reports import ReportRowOut
from app.services.reports import ReportsService


def _parse_dt(s: str | None) -> datetime | None:
    """Безопасно преобразует ISO-строку в datetime.

    Возвращает None при пустом значении или некорректном формате.
    """
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _parse_stations(station_objects: list[str] | None) -> list[str] | None:
    """
    Очищает и валидирует список объектов подстанций.

    FastAPI может передать `[""]` при пустом параметре массива.
    Функция отбрасывает пустые строки и возвращает None, если список пуст.
    """
    if not station_objects:
        return None
    cleaned = [s.strip() for s in station_objects if s.strip()]
    return cleaned or None


def clean_param(p: str | None) -> str | None:
    """Удаляет пробельные символы по краям строки.

    Если после очистки строка пуста — возвращает None.
    """
    if p is None:
        return None
    stripped = p.strip()
    return stripped if stripped else None


router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get(
    "/departments",
    response_model=List[str],
    summary="Справочник отделов",
    description="Возвращает список всех уникальных отделов, присутствующих в системе. Используется для фильтрации в интерфейсе.",
)
async def get_departments_list(
    session: AsyncSession = Depends(lifespan_session),
    user: CurrentUser = Depends(get_current_user),
) -> List[str]:
    """
    Возвращает список всех уникальных отделов пользователей.

    Используется фронтендом для построения фильтров.

    Args:
        session: Асинхронная сессия БД.
        user: Текущий авторизованный пользователь.

    Returns:
        List[str]: Уникальные названия отделов.
    """
    service = ReportsService(session)
    return await service.get_departments()


@router.get(
    "",
    response_model=list[ReportRowOut],
    summary="Получение отчета в JSON",
    description="Возвращает отфильтрованный список документов согласно переданным параметрам. Все фильтры опциональны.",
)
async def get_report(
    station_object: list[str] | None = Query(default=None, description="Объекты подстанций"),
    station_no: str | None = Query(default=None, description="Номер подстанции"),
    label: str | None = Query(default=None, description="Маркировка"),
    factory_no: str | None = Query(default=None, description="Заводской номер"),
    order_no: str | None = Query(default=None, description="Номер заказа"),
    date_from: str | None = Query(default=None, description="Дата регистрации с (ISO format)"),
    date_to: str | None = Query(default=None, description="Дата регистрации по (ISO format)"),
    doc_name: str | None = Query(default=None, description="Название документа"),
    username: str | None = Query(default=None, description="Логин сотрудника"),
    department: str | None = Query(default=None, description="Отдел сотрудника"),
    session: AsyncSession = Depends(lifespan_session),
    user: CurrentUser = Depends(get_current_user),
) -> list[ReportRowOut]:
    """
    Формирует аналитический отчет в формате JSON.

    Поддерживает гибкую фильтрацию по оборудованию, периоду регистрации,
    названию документа, пользователю и отделу. Все параметры опциональны.

    Args:
        station_object: Список объектов подстанций.
        station_no: Номер подстанции.
        label: Маркировка оборудования.
        factory_no: Заводской номер.
        order_no: Номер заказа.
        date_from: Начальная дата регистрации.
        date_to: Конечная дата регистрации.
        doc_name: Название документа.
        username: Логин пользователя.
        department: Отдел пользователя.
        session: Асинхронная сессия БД.
        user: Текущий авторизованный пользователь.

    Returns:
        list[ReportRowOut]: Список записей отчета.
    """
    service = ReportsService(session)
    df = _parse_dt(date_from)
    dt = _parse_dt(date_to)
    stations = _parse_stations(station_object)

    rows = await service.get_rows_extended(
        station_objects=stations,
        station_no=clean_param(station_no),
        label=clean_param(label),
        factory_no=clean_param(factory_no),
        order_no=clean_param(order_no),
        date_from=df,
        date_to=dt,
        doc_name=clean_param(doc_name),
        username=clean_param(username),
        department=clean_param(department),
    )
    return rows


@router.get(
    "/export",
    response_class=FileResponse,
    summary="Экспорт отчета в Excel",
    description=(
        "Генерирует и возвращает Excel-файл (.xlsx) по заданным фильтрам. "
        "После скачивания файл автоматически удаляется с сервера."
    ),
)
async def export_report_excel(
    station_object: list[str] | None = Query(default=None),
    station_no: str | None = Query(default=None),
    label: str | None = Query(default=None),
    factory_no: str | None = Query(default=None),
    order_no: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    doc_name: str | None = Query(default=None),
    username: str | None = Query(default=None),
    department: str | None = Query(default=None),
    session: AsyncSession = Depends(lifespan_session),
    user: CurrentUser = Depends(get_current_user),
) -> FileResponse:
    """
    Экспортирует отфильтрованные данные в Excel-файл.

    Использует BackgroundTask для автоматического удаления временного файла
    сразу после передачи его пользователю.

    Args:
        station_object: Список объектов подстанций.
        station_no, label, factory_no, order_no, doc_name, username, department: Параметры фильтрации.
        date_from, date_to: Период регистрации в ISO-формате.
        session: Асинхронная сессия БД.
        user: Текущий авторизованный пользователь.

    Returns:
        FileResponse: Excel-файл для скачивания.
    """
    service = ReportsService(session)
    df = _parse_dt(date_from)
    dt = _parse_dt(date_to)
    stations = _parse_stations(station_object)

    fname = await service.export_excel_extended(
        station_objects=stations,
        station_no=clean_param(station_no),
        label=clean_param(label),
        factory_no=clean_param(factory_no),
        order_no=clean_param(order_no),
        date_from=df,
        date_to=dt,
        doc_name=clean_param(doc_name),
        username=clean_param(username),
        department=clean_param(department),
    )

    return FileResponse(
        path=fname,
        filename=os.path.basename(fname),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        background=BackgroundTask(lambda: os.remove(fname)),
    )


@router.get(
    "/admin/documents",
    response_model=List[AdminDocumentRow],
    summary="Поиск документов для редактирования (Админ)",
    description="Административный поиск документов. Возвращает данные, необходимые для перехода в режим редактирования.",
)
async def admin_documents_search(
    station_object: list[str] | None = Query(default=None),
    station_no: str | None = Query(default=None),
    label: str | None = Query(default=None),
    factory_no: str | None = Query(default=None),
    order_no: str | None = Query(default=None),
    username: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    eq_type: str | None = Query(default=None),
    doc_name: str | None = Query(default=None),
    session: AsyncSession = Depends(lifespan_session),
    user: CurrentUser = Depends(get_current_user),
) -> List[AdminDocumentRow]:
    """
    Расширенный поиск документов, доступный только администраторам.

    Используется в административной панели для поиска документов с целью
    их последующего редактирования. Включает дополнительный фильтр по типу оборудования.

    Args:
        station_object: Список объектов подстанций.
        ... (остальные фильтры аналогичны основному отчету)
        eq_type: Тип оборудования.
        session: Асинхронная сессия БД.
        user: Текущий пользователь.

    Returns:
        List[AdminDocumentRow]: Список документов с системными идентификаторами.

    Raises:
        HTTPException(403): Если пользователь не является администратором.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен",
        )

    service = ReportsService(session)
    df = _parse_dt(date_from)
    dt = _parse_dt(date_to)
    stations = _parse_stations(station_object)

    rows = await service.get_rows_extended_admin(
        station_objects=stations,
        station_no=clean_param(station_no),
        label=clean_param(label),
        factory_no=clean_param(factory_no),
        order_no=clean_param(order_no),
        username=clean_param(username),
        date_from=df,
        date_to=dt,
        eq_type=clean_param(eq_type),
        doc_name=clean_param(doc_name),
    )
    return rows
