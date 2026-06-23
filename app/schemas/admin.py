"""
Модуль Pydantic-схем для административной панели.

Содержит модели данных, используемые исключительно в административных сценариях:
- Редактирование документов и связанного оборудования
- Административный расширенный поиск документов
- Получение списка доступных «золотых» номеров

Все схемы используют `from_attributes=True` для прямой конвертации SQLAlchemy-моделей.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GoldenSuggestOut(BaseModel):
    """
    Схема ответа с предложенными «золотыми» номерами.

    Используется при резервировании круглых номеров (заканчивающихся на 00),
    доступном только администраторам.
    """
    golden_numbers: list[int] = Field(
        ..., 
        description="Список доступных золотых номеров (кратных 100)."
    )


class AdminDocumentUpdate(BaseModel):
    """
    Схема для обновления документа и связанного оборудования администратором (PATCH).

    Все поля являются опциональными, что позволяет частично обновлять запись.
    Поддерживает одновременное изменение метаданных документа и характеристик оборудования.
    """
    # --- Поля из модели Document ---
    doc_name: str | None = Field(default=None, description="Новое название документа")
    note: str | None = Field(default=None, description="Новое примечание к документу")

    # --- Поля из модели Equipment ---
    eq_type: str | None = Field(default=None, description="Тип оборудования")
    station_object: str | None = Field(default=None, description="Объект подстанции")
    station_no: str | None = Field(default=None, description="Номер подстанции")
    factory_no: str | None = Field(default=None, description="Заводской номер оборудования")
    order_no: str | None = Field(default=None, description="Номер заказа/договора")
    label: str | None = Field(default=None, description="Условное обозначение/маркировка")

    model_config = ConfigDict(from_attributes=True)


class AdminDocumentRow(BaseModel):
    """
    Расширенная схема одной строки административного поиска документов.

    Объединяет данные из моделей `Document`, `Equipment` и `User`.
    Используется в административной панели для поиска документов с целью
    их последующего редактирования. Содержит все необходимые идентификаторы
    (`id`, `eq_id`, `doc_no`) для построения ссылок на формы редактирования.
    """
    id: int = Field(..., description="Внутренний ID документа")
    doc_no: str = Field(..., description="Отформатированный регистрационный номер (например, УТЗ-000100)")
    numeric: int = Field(..., description="Числовое значение номера (для сортировки)")
    reg_date: str = Field(..., description="Дата и время регистрации в формате ISO 8601")
    doc_name: str = Field(..., description="Название документа")
    note: str | None = Field(default=None, description="Примечание к документу")

    eq_id: int = Field(..., description="Внутренний ID оборудования")
    eq_type: str = Field(..., description="Тип оборудования")
    factory_no: str | None = Field(default=None, description="Заводской номер")
    order_no: str | None = Field(default=None, description="Номер заказа")
    label: str | None = Field(default=None, description="Маркировка оборудования")
    station_no: str | None = Field(default=None, description="Номер подстанции")
    station_object: str | None = Field(default=None, description="Объект подстанции")

    username: str = Field(..., description="Логин пользователя, зарегистрировавшего документ")

    model_config = ConfigDict(from_attributes=True)
