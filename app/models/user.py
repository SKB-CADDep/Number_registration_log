"""
Модуль ORM-модели пользователей.

Содержит модель User, которая выступает локальным кэшем/справочником 
сотрудников. Данные синхронизируются с LDAP (Active Directory) при 
авторизации через JWT. Используется для привязки документов и сессий 
резервирования номеров к конкретным пользователям.
"""

from __future__ import annotations

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import CITEXT

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """
    Модель пользователя системы (таблица 'users').

    Представляет собой локальную копию учётных записей из Active Directory.
    Основной идентификатор — поле `username`.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
        doc="Внутренний уникальный идентификатор пользователя в системе.",
    )

    username: Mapped[str] = mapped_column(
        CITEXT,
        nullable=False,
        unique=True,
        doc="Логин пользователя (совпадает с учетной записью домена Active Directory).",
    )

    last_name: Mapped[str | None] = mapped_column(
        nullable=True,
        doc="Фамилия сотрудника, полученная из LDAP.",
    )

    first_name: Mapped[str | None] = mapped_column(
        nullable=True,
        doc="Имя сотрудника, полученное из LDAP.",
    )

    middle_name: Mapped[str | None] = mapped_column(
        nullable=True,
        doc="Отчество сотрудника (если есть).",
    )

    department: Mapped[str | None] = mapped_column(
        nullable=True,
        doc="Подразделение/отдел, в котором работает сотрудник (кэшируется из LDAP).",
    )
