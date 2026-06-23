"""
Модуль Pydantic-схем для работы с сессиями резервирования номеров.

Содержит модели запросов и ответов, используемые при:
- Создании новой сессии резервирования
- Добавлении дополнительных номеров в сессию
- Возврате информации о сессии и результате резервирования

Используется в роутере `/sessions` и сервисе `ReservationService`.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SessionStart(BaseModel):
    """
    Схема запроса на создание новой сессии резервирования.

    Используется при старте процесса массовой регистрации документов.
    Определяет, сколько номеров нужно зарезервировать и за каким оборудованием.
    """
    equipment_id: int = Field(..., description="ID оборудования, за которым резервируются номера")
    requested_count: int = Field(
        1, 
        ge=1, 
        le=1000, 
        description="Количество номеров, которые нужно зарезервировать (от 1 до 1000)"
    )
    ttl_seconds: int | None = Field(
        default=None, 
        description="Время жизни сессии в секундах. Если не указано, используется значение по умолчанию из настроек"
    )


class SessionOut(BaseModel):
    """
    Полная схема сессии резервирования для ответа API.

    Возвращает актуальное состояние сессии (статус, сроки жизни, параметры).
    """
    id: str = Field(..., description="UUID сессии")
    user_id: int = Field(..., description="ID пользователя, создавшего сессию")
    equipment_id: int = Field(..., description="ID связанного оборудования")
    requested_count: int = Field(..., description="Запрошенное количество номеров")
    status: str = Field(..., description="Текущий статус сессии (active, completed, expired и др.)")
    ttl_seconds: int = Field(..., description="Время жизни сессии в секундах")
    created_at: datetime = Field(..., description="Дата и время создания сессии")
    expires_at: datetime = Field(..., description="Дата и время истечения сессии")

    model_config = ConfigDict(from_attributes=True)


class ReserveResult(BaseModel):
    """
    Схема результата резервирования номеров.

    Возвращается после успешного создания сессии и захвата номеров.
    """
    session_id: str = Field(..., description="UUID созданной сессии резервирования")
    reserved_numbers: list[int] = Field(
        ..., 
        description="Список успешно зарезервированных номеров"
    )


class AddNumbers(BaseModel):
    """
    Схема для добавления дополнительных номеров в уже существующую сессию.

    Позволяет «дозаказать» номера, если изначально зарезервированного количества не хватило.
    Поддерживает как обычные, так и золотые номера.
    """
    requested_count: int | None = Field(
        default=None, 
        description="Количество дополнительных обычных номеров для автоматического резервирования"
    )
    numbers: list[int] | None = Field(
        default=None, 
        description="Конкретные номера, которые пользователь хочет зарезервировать"
    )
    quantity_golden: int | None = Field(
        default=None, 
        description="Количество золотых номеров (заканчивающихся на 00) для резервирования"
    )
