"""
Модуль бизнес-логики работы с пользователями.

Предоставляет сервисный слой для получения или создания локальных профилей
пользователей на основе логина из внешней системы авторизации (LDAP/Active Directory).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.users import UsersRepository
from app.models.user import User


class UsersService:
    """
    Сервис для работы с пользователями системы.

    Основная ответственность — реализация паттерна "Get or Create" по `username`.
    Используется при обработке JWT-токена и при импорте исторических данных,
    чтобы автоматически создавать локальные профили пользователей из внешних систем.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация сервиса с репозиторием пользователей."""
        self.session = session
        self.repo = UsersRepository(session)

    async def get_or_create_by_username(self, username: str) -> User:
        """
        Возвращает существующего пользователя или создаёт нового по логину.

        Если пользователь с таким `username` уже есть в базе — возвращает его.
        Если нет — создаёт новую запись и фиксирует изменения в базе данных.

        Этот метод гарантирует наличие локального профиля пользователя
        при первой авторизации через внешнюю систему (LDAP/AD).

        Args:
            username: Логин пользователя из Active Directory / LDAP.

        Returns:
            User: Объект пользователя (существующий или только что созданный).
        """
        user = await self.repo.get_by_username(username)
        if not user:
            user = await self.repo.create(username)
            await self.session.commit()
        return user
