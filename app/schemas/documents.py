"""
Модуль Pydantic-схем для работы с документами и резервированием номеров.

Содержит модели запросов и ответов, используемые в эндпоинтах:
- Назначение регистрационного номера документу
- Вывод информации о документе
- Резервирование «золотых» номеров (административная функция)

Схемы используются в роутере `/documents` и соответствующих сервисах.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentAssignOne(BaseModel):
    """
    Схема запроса на назначение одного регистрационного номера документу.

    Используется при создании документа в рамках активной сессии резервирования.
    Содержит ссылку на сессию, название документа и опциональное примечание.
    """
    session_id: str = Field(..., description="UUID активной сессии резервирования")
    doc_name: str = Field(..., min_length=1, description="Название документа")
    note: str | None = Field(default=None, description="Примечание к документу")
    numeric: int = Field(..., description="Числовое значение регистрационного номера")


class DocumentOut(BaseModel):
    """
    Базовая схема ответа с информацией о зарегистрированном документе.

    Используется для возврата данных после успешного назначения номера.
    Включает как сырые данные, так и отформатированный номер документа.
    """
    id: int = Field(..., description="Внутренний ID документа")
    numeric: int = Field(..., description="Числовое значение номера")
    formatted_no: str = Field(..., description="Отформатированный номер (например: УТЗ-000100)")
    reg_date: datetime = Field(..., description="Дата и время регистрации документа")
    doc_name: str = Field(..., description="Название документа")
    note: str | None = Field(default=None, description="Примечание к документу")
    equipment_id: int = Field(..., description="ID связанного оборудования")
    user_id: int = Field(..., description="ID пользователя, создавшего документ")

    model_config = ConfigDict(from_attributes=True)


class GoldenNumberReservationRequest(BaseModel):
    """
    Схема запроса на резервирование «золотых» (круглых) номеров.

    Доступна только администраторам. Используется для выделения номеров,
    заканчивающихся на 00, под важные проекты или контракты.
    """
    quantity: int = Field(
        ..., 
        gt=0, 
        description="Количество золотых номеров для резервирования"
    )
    equipment_id: int = Field(
        ..., 
        description="ID оборудования, к которому будут привязаны резервируемые номера"
    )
    ttl_seconds: int = Field(
        default=3600,
        gt=0,
        description="Время жизни сессии резервирования в секундах (по умолчанию 1 час)"
    )


class GoldenNumberReservationResponse(BaseModel):
    """
    Схема ответа после успешного резервирования «золотых» номеров.

    Возвращает идентификатор созданной сессии и список зарезервированных номеров.
    """
    session_id: str = Field(..., description="UUID созданной сессии резервирования")
    reserved_numbers: list[int] = Field(
        ..., 
        description="Список зарезервированных золотых номеров"
    )
