from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from datetime import datetime


class ReportFilter(BaseModel):
    station_objects: list[str] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class ReportRow(BaseModel):
    doc_no: str
    reg_date: datetime
    doc_name: str
    note: str
    eq_type: str
    factory_no: str | None
    order_no: str | None
    label: str | None
    station_no: str | None
    station_object: str | None
    last_name: str | None
    first_name: str | None
    middle_name: str | None
    department: str | None
    username_fallback: str | None


class ReportRowOut(BaseModel):
    """Схема для одной строки отчета, как она возвращается API."""
    doc_no: str
    numeric: int
    reg_date: str
    doc_name: str
    note: str | None
    eq_type: str
    factory_no: str | None
    order_no: str | None
    label: str | None
    station_no: str | None
    station_object: str | None
    username: str
    department: str | None

    model_config = ConfigDict(from_attributes=True)