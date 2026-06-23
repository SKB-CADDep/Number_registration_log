"""
Модуль репозитория для работы с сессиями резервирования номеров.

Реализует паттерн Repository для управления жизненным циклом сессий.
Сессии используются для временной блокировки (резервирования) пула 
регистрационных номеров за конкретным пользователем и оборудованием.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session, SessionStatus


class SessionsRepository:
    """
    Репозиторий для управления таблицей `sessions`.

    Отвечает за создание сессий резервирования, получение информации о них,
    изменение статуса и автоматическое истечение просроченных сессий.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория."""
        self.session = session

    async def create(
        self,
        *,
        user_id: int,
        equipment_id: int,
        requested_count: int,
        ttl_seconds: int,
    ) -> Session:
        """
        Создаёт новую активную сессию резервирования номеров.

        Автоматически рассчитывает `expires_at` и устанавливает статус `active`.
        Выполняет `flush()`, чтобы объект сессии получил сгенерированный UUID
        и мог быть использован дальше в рамках текущей транзакции.

        Args:
            user_id: ID пользователя, создающего сессию.
            equipment_id: ID оборудования, для которого резервируются номера.
            requested_count: Количество номеров, которое хочет зарезервировать пользователь.
            ttl_seconds: Время жизни сессии в секундах (Time To Live).

        Returns:
            Session: Созданная сессия.
        """
        now = datetime.utcnow()

        new_session = Session(
            user_id=user_id,
            equipment_id=equipment_id,
            requested_count=requested_count,
            ttl_seconds=ttl_seconds,
            status=SessionStatus.active,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )

        self.session.add(new_session)
        await self.session.flush()
        return new_session

    async def get(self, session_id: str) -> Session | None:
        """Возвращает сессию по её уникальному идентификатору (UUID)."""
        result = await self.session.execute(
            select(Session).where(Session.id == session_id)
        )
        return result.scalars().first()

    async def set_status(self, session_id: str, status: SessionStatus) -> None:
        """
        Обновляет статус сессии.

        Используется для перевода сессии в состояние `completed`, `cancelled`
        или других допустимых статусов.
        """
        await self.session.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(status=status)
        )

    async def expire_old(self, now: datetime) -> int:
        """
        Помечает все просроченные активные сессии как `expired`.

        Это фоновая задача (сборщик мусора), которая должна периодически запускаться.

        Args:
            now: Текущее серверное время (UTC). Передаётся явно для возможности тестирования.

        Returns:
            int: Количество сессий, которые были помечены как просроченные.
        """
        result = await self.session.execute(
            update(Session)
            .where(
                Session.status == SessionStatus.active,
                Session.expires_at < now,
            )
            .values(status=SessionStatus.expired)
            .returning(Session.id)
        )
        return len(result.fetchall())
