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

router = APIRouter()


def _parse_dt(s: str | None) -> datetime | None:
    if not s: return None
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _parse_stations(station_objects: list[str] | None) -> list[str] | None:
    if not station_objects: return None
    # FastAPI с Query(default=None) может передавать [""] если параметр пуст
    cleaned = [s.strip() for s in station_objects if s.strip()]
    return cleaned or None


def clean_param(p: str | None) -> str | None:
    if p is None: return None
    stripped = p.strip()
    return stripped if stripped else None


# --- НОВЫЙ ЭНДПОИНТ (Должен быть здесь) ---
@router.get("/departments", response_model=List[str])
async def get_departments_list(
    session: AsyncSession = Depends(lifespan_session),
    user: CurrentUser = Depends(get_current_user),
):
    """Список всех отделов для фильтрации."""
    svc = ReportsService(session)
    return await svc.get_departments()
# ------------------------------------------


@router.get("", response_model=list[ReportRowOut])
async def get_report(
        station_object: list[str] | None = Query(default=None),
        station_no: str | None = Query(default=None),
        label: str | None = Query(default=None),
        factory_no: str | None = Query(default=None),
        order_no: str | None = Query(default=None),
        date_from: str | None = Query(default=None),
        date_to: str | None = Query(default=None),
        doc_name: str | None = Query(default=None),
        username: str | None = Query(default=None),
        department: str | None = Query(default=None), # <--- Параметр фильтрации
        session: AsyncSession = Depends(lifespan_session),
        user: CurrentUser = Depends(get_current_user),
):
    """Получение отчета с фильтрами. Всегда возвращает JSON."""
    svc = ReportsService(session)
    df = _parse_dt(date_from)
    dt = _parse_dt(date_to)
    stations = _parse_stations(station_object)

    rows = await svc.get_rows_extended(
        station_objects=stations,
        station_no=clean_param(station_no),
        label=clean_param(label),
        factory_no=clean_param(factory_no),
        order_no=clean_param(order_no),
        date_from=df,
        date_to=dt,
        doc_name=clean_param(doc_name),
        username=clean_param(username),
        department=clean_param(department) # <--- Передача в сервис
    )
    return rows


@router.get("/export", response_class=FileResponse)
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
        department: str | None = Query(default=None), # <--- Параметр фильтрации
        session: AsyncSession = Depends(lifespan_session),
        user: CurrentUser = Depends(get_current_user),
):
    """Экспорт отчета в Excel. Возвращает файл."""
    svc = ReportsService(session)
    df = _parse_dt(date_from)
    dt = _parse_dt(date_to)
    stations = _parse_stations(station_object)

    fname = await svc.export_excel_extended(
        station_objects=stations,
        station_no=clean_param(station_no),
        label=clean_param(label),
        factory_no=clean_param(factory_no),
        order_no=clean_param(order_no),
        date_from=df,
        date_to=dt,
        doc_name=clean_param(doc_name),
        username=clean_param(username),
        department=clean_param(department) # <--- Передача в сервис
    )

    return FileResponse(
        path=fname,
        filename=os.path.basename(fname),
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        background=BackgroundTask(lambda: os.remove(fname))
    )


@router.get("/admin/documents", response_model=List[AdminDocumentRow])
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
):
    """Расширенный поиск документов для админов."""
    if not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Доступ запрещен")

    svc = ReportsService(session)
    df = _parse_dt(date_from)
    dt = _parse_dt(date_to)
    stations = _parse_stations(station_object)

    rows = await svc.get_rows_extended_admin(
        station_objects=stations, station_no=clean_param(station_no), label=clean_param(label),
        factory_no=clean_param(factory_no), order_no=clean_param(order_no), username=clean_param(username),
        date_from=df, date_to=dt, eq_type=clean_param(eq_type), doc_name=clean_param(doc_name)
    )
    return rows