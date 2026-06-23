"""
Модуль бизнес-логики резервирования регистрационных номеров.

Отвечает за управление жизненным циклом сессий резервирования:
- Создание сессии и резервирование пакета номеров
- Дозаказ номеров в существующую сессию
- Резервирование «золотых» номеров (только для администраторов)
- Освобождение номеров при отмене сессии

Содержит сложную логику приоритезации: сначала используются ранее освобождённые
номера (`released`), затем генерируются новые. Защищает «золотые» номера
(кратные 100) от использования обычными пользователями.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import update, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.doc_number import DocNumber, DocNumStatus
from app.models.session import SessionStatus, Session
from app.repositories.counter import CounterRepository
from app.repositories.doc_numbers import DocNumbersRepository
from app.repositories.sessions import SessionsRepository
from app.utils.numbering import is_golden


class ReservationService:
    """
    Сервис управления резервированием номеров.

    Координирует работу `SessionsRepository`, `DocNumbersRepository` и `CounterRepository`.
    Обеспечивает атомарность операций резервирования и соблюдение бизнес-правил
    по «золотым» номерам.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация сервиса с необходимыми репозиториями."""
        self.session = session
        self.sessions_repo = SessionsRepository(session)
        self.numbers_repo = DocNumbersRepository(session)
        self.counter_repo = CounterRepository(session)

    async def reserve_golden_numbers(
        self, *, user_id: int, equipment_id: int, quantity: int, ttl_seconds: int
    ) -> tuple[str, list[int]]:
        """
        Резервирует указанное количество «золотых» номеров (кратных 100).

        Доступно **только администраторам**. Создаёт отдельную сессию
        и резервирует конкретные номера.

        Args:
            user_id: ID пользователя (администратора).
            equipment_id: ID оборудования, к которому привязывается резерв.
            quantity: Количество запрашиваемых золотых номеров.
            ttl_seconds: Время жизни резервации.

        Returns:
            tuple[str, list[int]]: (session_id, список зарезервированных номеров)

        Raises:
            ValueError: Если не удалось найти достаточное количество свободных золотых номеров.
        """
        candidates = await self._find_free_golden_numbers(quantity)

        if len(candidates) < quantity:
            raise ValueError(f"Не удалось найти {quantity} свободных 'золотых' номеров.")

        sess = await self.sessions_repo.create(
            user_id=user_id,
            equipment_id=equipment_id,
            requested_count=len(candidates),
            ttl_seconds=ttl_seconds,
        )
        reserved = await self.numbers_repo.reserve_specific_numbers(
            candidates, user_id, sess.id, ttl_seconds
        )

        await self.session.commit()
        return sess.id, reserved

    async def start_session(
        self, *, user_id: int, equipment_id: int, requested_count: int, ttl_seconds: int
    ) -> tuple[str, list[int]]:
        """
        Создаёт новую сессию резервирования и резервирует запрошенное количество номеров.

        Основной метод для обычных пользователей. Использует приоритетную логику:
        сначала released-номера, затем генерация новых.

        Args:
            user_id: ID пользователя.
            equipment_id: ID оборудования.
            requested_count: Сколько номеров зарезервировать.
            ttl_seconds: Время жизни сессии.

        Returns:
            tuple[str, list[int]]: (session_id, список зарезервированных номеров)
        """
        sess = await self.sessions_repo.create(
            user_id=user_id,
            equipment_id=equipment_id,
            requested_count=requested_count,
            ttl_seconds=ttl_seconds,
        )

        reserved = await self._reserve_for_session(
            session_id=sess.id,
            user_id=user_id,
            count=requested_count,
            ttl_seconds=ttl_seconds,
            is_admin=False,
        )

        await self.session.commit()
        return sess.id, reserved

    async def _reserve_for_session(
        self,
        *,
        session_id: str,
        user_id: int,
        count: int,
        is_admin: bool,
        ttl_seconds: int,
    ) -> list[int]:
        """
        Внутренний метод резервирования номеров для сессии.

        Логика работы (по приоритету):
        1. Берёт номера из пула ранее освобождённых (`released`).
        2. Если не хватило — генерирует новые номера, пропуская «золотые»
           для не-администраторов.

        Обновляет `next_normal_start` в счётчике при генерации новых номеров.
        """
        await self.numbers_repo.release_expired()

        counter = await self.counter_repo.get_for_update()
        base_start = counter.base_start
        reserved_total: list[int] = []

        # 1. Сначала пытаемся использовать ранее освобождённые номера
        released_pick = await self.numbers_repo.fetch_released_for_update(
            base_start=base_start, limit=count, skip_golden=not is_admin
        )
        if released_pick:
            reserved = await self.numbers_repo.reserve_existing(
                released_pick, user_id, session_id, ttl_seconds
            )
            reserved_total.extend(reserved)

        need_more = count - len(reserved_total)
        if need_more > 0:
            # 2. Генерируем новые номера
            candidate = max(counter.next_normal_start, base_start)
            new_candidates: list[int] = []

            while len(new_candidates) < need_more:
                if not is_admin and is_golden(candidate):
                    candidate += 1
                    continue
                new_candidates.append(candidate)
                candidate += 1

            reserved = await self.numbers_repo.create_and_reserve_new(
                new_candidates,
                user_id=user_id,
                session_id=session_id,
                ttl_seconds=ttl_seconds,
            )
            reserved_total.extend(reserved)

            # Обновляем счётчик
            counter.next_normal_start = candidate

        return sorted(reserved_total)

    async def add_numbers_to_session(
        self,
        *,
        session_id: str,
        user_id: int,
        requested_count: int | None = None,
        numbers: list[int] | None = None,
        quantity_golden: int | None = None,
        is_admin: bool,
    ) -> list[int]:
        """
        Добавляет дополнительные номера в уже существующую активную сессию.

        Поддерживает три режима (взаимоисключающие):
        - `requested_count` — автоматический дозаказ обычных номеров
        - `numbers` — резервирование конкретных номеров
        - `quantity_golden` — резервирование золотых номеров (только админ)

        Также продлевает время жизни всей сессии и всех номеров в ней.

        Args:
            session_id: UUID существующей сессии.
            user_id: ID пользователя.
            requested_count: Количество дополнительных обычных номеров.
            numbers: Конкретные номера для резервирования.
            quantity_golden: Количество золотых номеров.
            is_admin: Флаг администратора (нужен для золотых номеров).

        Returns:
            list[int]: Список newly зарезервированных номеров.

        Raises:
            ValueError: Если сессия не найдена, недостаточно золотых номеров,
                        или обычный пользователь пытается зарезервировать золотые номера.
        """
        sess = await self.sessions_repo.get(session_id)
        if not sess:
            raise ValueError("Сессия не найдена.")

        ttl = sess.ttl_seconds
        new_expires_at = datetime.utcnow() + timedelta(seconds=ttl)

        # Продлеваем жизнь сессии и всех номеров в ней
        await self.session.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(expires_at=new_expires_at)
        )
        await self.session.execute(
            update(DocNumber)
            .where(DocNumber.session_id == session_id)
            .values(expires_at=new_expires_at)
        )

        newly_reserved = []

        if requested_count:
            newly_reserved = await self._reserve_for_session(
                session_id=session_id,
                user_id=user_id,
                count=requested_count,
                ttl_seconds=ttl,
                is_admin=is_admin,
            )
        elif numbers:
            newly_reserved = await self.numbers_repo.reserve_specific_numbers(
                numbers, user_id, session_id, ttl
            )
        elif quantity_golden:
            if not is_admin:
                raise ValueError("Только администраторы могут резервировать 'золотые' номера.")

            candidates = await self._find_free_golden_numbers(quantity_golden)

            if len(candidates) < quantity_golden:
                raise ValueError(f"Не удалось найти {quantity_golden} свободных 'золотых' номеров.")

            newly_reserved = await self.numbers_repo.reserve_specific_numbers(
                candidates, user_id, session_id, ttl
            )

        await self.session.commit()
        return newly_reserved

    async def _find_free_golden_numbers(self, quantity: int) -> list[int]:
        """
        Находит указанное количество свободных «золотых» номеров.

        Ищет начиная от текущего счётчика, пропуская уже назначенные или
        зарезервированные номера. Используется только администраторами.
        """
        counter = await self.counter_repo.get_for_update()

        start_point = max(counter.next_normal_start, counter.base_start)
        start_golden = ((start_point + 99) // 100) * 100

        stmt = select(DocNumber.numeric).where(
            DocNumber.status.in_([DocNumStatus.assigned, DocNumStatus.reserved])
        )
        result = await self.session.execute(stmt)
        occupied_numbers = set(result.scalars().all())

        candidates = []
        current_check = start_golden
        while len(candidates) < quantity:
            if current_check not in occupied_numbers:
                candidates.append(current_check)
            current_check += 100
            if current_check > 999900:
                break

        return candidates

    async def cancel_session(self, session_id: str) -> int:
        """
        Отменяет сессию и освобождает все зарезервированные, но не использованные номера.

        Args:
            session_id: UUID сессии.

        Returns:
            int: Количество освобождённых номеров.
        """
        await self.sessions_repo.set_status(session_id, SessionStatus.cancelled)
        released = await self.numbers_repo.release_session(session_id)
        await self.session.commit()
        return released
