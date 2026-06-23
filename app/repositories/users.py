"""
Модуль репозитория для работы с пользователями системы.

Реализует паттерн Repository для управления сущностью User.
Обеспечивает создание локальных профилей пользователей при первой авторизации
через LDAP/Active Directory, а также поиск по внутреннему ID и username.

Репозиторий не выполняет `commit()`. Сохранение изменений остаётся на уровне
сервиса (Unit of Work).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UsersRepository:
    """
    Репозиторий для управления таблицей `users`.

    Отвечает за создание и поиск пользователей в локальной базе.
    Пользователи создаются как "локальный кэш" профиля из внешней системы
    авторизации (LDAP/AD) при первом входе в систему.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализирует репозиторий с переданной асинхронной сессией SQLAlchemy."""
        self.session = session

    async def get(self, id_: int) -> User | None:
        """
        Возвращает пользователя по его внутреннему системному ID.

        Args:
            id_: Внутренний первичный ключ пользователя в базе.

        Returns:
            Объект User, если найден, иначе None.
        """
        result = await self.session.execute(
            select(User).where(User.id == id_)
        )
        return result.scalars().first()

    async def get_by_username(self, username: str) -> User | None:
        """
        Возвращает пользователя по его уникальному логину (username).

        Используется при обработке JWT-токена для привязки внешнего пользователя
        к внутреннему профилю системы (аудит, сессии резервирования номеров и т.д.).

        Args:
            username: Логин пользователя из Active Directory / LDAP.

        Returns:
            Объект User, если найден, иначе None.
        """
        result = await self.session.execute(
            select(User).where(User.username == username)
        )
        return result.scalars().first()

    async def create(self, username: str) -> User:
        """
        Создаёт нового пользователя (локальный кэш профиля из LDAP/AD).

        Выполняет `flush()`, чтобы объект сразу получил сгенерированный первичный ключ `id`.

        Важно: метод не вызывает `commit()`. Сохранение остаётся на уровне вызывающего сервиса.

        Args:
            username: Логин пользователя из Active Directory.

        Returns:
            Созданный объект пользователя с заполненным `id`.
        """
        user = User(username=username)
        self.session.add(user)
        await self.session.flush()
        return user
