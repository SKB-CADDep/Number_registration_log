"""
Модуль Pydantic-схем для формирования отчетов.

Содержит модели для фильтрации данных, внутреннего представления строк отчёта,
а также схему ответа, возвращаемую клиентам (JSON + Excel-экспорт).

Используется в роутере `/reports` и сервисе `ReportsService`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportFilter(BaseModel):
    """
    Схема фильтров для построения отчетов.

    Используется внутри сервиса `ReportsService` для передачи параметров
    фильтрации из API-роутера в методы получения данных.
    """
    station_objects: list[str] | None = Field(
        default=None, description="Список объектов подстанций для фильтрации"
    )
    date_from: datetime | None = Field(
        default=None, description="Начальная дата регистрации документа"
    )
    date_to: datetime | None = Field(
        default=None, description="Конечная дата регистрации документа"
    )


class ReportRow(BaseModel):
    """
    Внутренняя схема одной строки отчёта.

    Используется на уровне сервиса для работы с сырыми данными из базы
    (включая информацию о пользователе в формате ФИО + department).
    Не возвращается напрямую клиенту.
    """
    doc_no: str = Field(..., description="Отформатированный регистрационный номер")
    reg_date: datetime = Field(..., description="Дата регистрации документа")
    doc_name: str = Field(..., description="Название документа")
    note: str = Field(..., description="Примечание к документу")
    eq_type: str = Field(..., description="Тип оборудования")
    factory_no: str | None = Field(default=None, description="Заводской номер")
    order_no: str | None = Field(default=None, description="Номер заказа")
    label: str | None = Field(default=None, description="Маркировка оборудования")
    station_no: str | None = Field(default=None, description="Станционный номер")
    station_object: str | None = Field(default=None, description="Объект подстанции")
    last_name: str | None = Field(default=None, description="Фамилия пользователя")
    first_name: str | None = Field(default=None, description="Имя пользователя")
    middle_name: str | None = Field(default=None, description="Отчество пользователя")
    department: str | None = Field(default=None, description="Отдел пользователя")
    username_fallback: str | None = Field(
        default=None, description="Логин пользователя (используется как fallback)"
    )


class ReportRowOut(BaseModel):
    """
    Схема одной строки отчёта, возвращаемая клиентам через API.

    Используется в эндпоинтах получения JSON-отчёта и при формировании Excel-файла.
    Содержит упрощённую информацию о пользователе (username вместо ФИО).
    """
    doc_no: str = Field(..., description="Отформатированный регистрационный номер")
    numeric: int = Field(..., description="Числовое значение номера (для сортировки)")
    reg_date: str = Field(..., description="Дата регистрации в формате ISO 8601 (строка)")
    doc_name: str = Field(..., description="Название документа")
    note: str | None = Field(default=None, description="Примечание к документу")
    eq_type: str = Field(..., description="Тип оборудования")
    factory_no: str | None = Field(default=None, description="Заводской номер")
    order_no: str | None = Field(default=None, description="Номер заказа")
    label: str | None = Field(default=None, description="Маркировка оборудования")
    station_no: str | None = Field(default=None, description="Станционный номер")
    station_object: str | None = Field(default=None, description="Объект подстанции")
    username: str = Field(..., description="Логин пользователя, создавшего документ")
    department: str | None = Field(default=None, description="Отдел пользователя")

    model_config = ConfigDict(from_attributes=True)
