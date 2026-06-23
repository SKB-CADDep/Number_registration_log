"""
Модуль Pydantic-схем для работы со справочником оборудования.

Содержит модели для создания новой записи оборудования и представления
существующих записей. Включает строгие валидаторы бизнес-правил для
заводского номера, номера заказа и станционного номера.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


class EquipmentCreate(BaseModel):
    """
    Схема создания новой единицы оборудования.

    Содержит валидацию ключевых полей:
    - `factory_no`: только цифры, максимум 5 символов
    - `order_no`: строго формат XXXXX-XX-XXXXX
    - `station_no`: только цифры, максимум 2 символа

    Все поля, кроме `eq_type`, являются опциональными.
    """
    eq_type: str = Field(..., min_length=1, description="Тип оборудования (обязательное поле)")
    factory_no: str | None = Field(
        default=None, 
        description="Заводской номер (только цифры, не более 5 символов)"
    )
    order_no: str | None = Field(
        default=None, 
        description="Номер заказа в формате XXXXX-XX-XXXXX"
    )
    label: str | None = Field(default=None, description="Маркировка / условное обозначение")
    station_no: str | None = Field(
        default=None, 
        description="Станционный номер (только цифры, не более 2 символов)"
    )
    station_object: str | None = Field(default=None, description="Объект подстанции")
    notes: str | None = Field(default=None, description="Дополнительные примечания")

    @field_validator("factory_no")
    @classmethod
    def validate_factory_no(cls, v: str | None) -> str | None:
        """Проверка: не более 5 символов и только цифры."""
        if v is None:
            return v
        if not v.isdigit():
            raise ValueError("Заводской номер должен содержать только цифры")
        if len(v) > 5:
            raise ValueError("Длина заводского номера не может превышать 5 символов")
        return v

    @field_validator("order_no")
    @classmethod
    def validate_order_no(cls, v: str | None) -> str | None:
        """Проверка: шаблон 5 цифр - 2 цифры - 5 цифр (XXXXX-XX-XXXXX)."""
        if v is None:
            return v
        if not re.match(r"^\d{5}-\d{2}-\d{5}$", v):
            raise ValueError("Номер заказа должен соответствовать шаблону XXXXX-XX-XXXXX")
        return v

    @field_validator("station_no")
    @classmethod
    def validate_station_no(cls, v: str | None) -> str | None:
        """Проверка: не более 2 символов и только цифры."""
        if v is None:
            return v
        if not v.isdigit():
            raise ValueError("Станционный номер должен содержать только цифры")
        if len(v) > 2:
            raise ValueError("Длина станционного номера не может превышать 2 символов")
        return v


class EquipmentOut(BaseModel):
    """
    Схема представления оборудования в ответах API.

    Используется при возврате данных оборудования в поиске, списках
    и автодополнении. Поддерживает автоматическую конверсию из SQLAlchemy-модели.
    """
    id: int = Field(..., description="Внутренний идентификатор оборудования")
    eq_type: str = Field(..., description="Тип оборудования")
    factory_no: str | None = Field(default=None, description="Заводской номер")
    order_no: str | None = Field(default=None, description="Номер заказа")
    label: str | None = Field(default=None, description="Маркировка / условное обозначение")
    station_no: str | None = Field(default=None, description="Станционный номер")
    station_object: str | None = Field(default=None, description="Объект подстанции")
    notes: str | None = Field(default=None, description="Дополнительные примечания")

    model_config = ConfigDict(from_attributes=True)
