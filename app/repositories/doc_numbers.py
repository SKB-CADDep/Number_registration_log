"""
Модуль репозитория для работы с пулом регистрационных номеров.

Реализует паттерн Repository и содержит всю бизнес-логику управления 
жизненным циклом регистрационных номеров: резервирование, назначение, 
освобождение по TTL, повторное использование освобождённых номеров.

Поддерживает обработку "золотых" номеров (кратных 100) и защищает 
от race condition с помощью блокировок на уровне базы данных.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select, update, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.doc_number import DocNumber, DocNumStatus


class DocNumbersRepository:
    """
    Репозиторий для управления таблицей `doc_numbers`.

    Отвечает за атомарное резервирование, повторное использование и 
    жизненный цикл регистрационных номеров. Все методы, изменяющие данные,
    выполняют `flush()`, но не делают `commit()` — коммит остаётся на уровне сервиса.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация репозитория."""
        self.session = session

    async def release_expired(self, now: datetime | None = None) -> int:
        """
        Освобождает номера, у которых истёк TTL (сборщик мусора).

        Args:
            now: Текущее время (используется для тестирования).

        Returns:
            int: Количество освобождённых номеров.
        """
        now = now or datetime.utcnow()

        result = await self.session.execute(
            update(DocNumber)
            .where(
                and_(
                    DocNumber.status == DocNumStatus.reserved,
                    DocNumber.expires_at < now,
                )
            )
            .values(
                status=DocNumStatus.released,
                released_at=now,
                expires_at=None,
                reserved_by=None,
                session_id=None,
            )
            .returning(DocNumber.id)
        )
        return len(result.fetchall())

    async def fetch_released_for_update(
        self, base_start: int, limit: int, skip_golden: bool = True
    ) -> list[DocNumber]:
        """
        Находит и блокирует ранее освобождённые номера для повторного использования.

        Использует `SELECT ... FOR UPDATE SKIP LOCKED`, чтобы избежать конкуренции.

        Args:
            base_start: Минимальный номер, с которого начинать поиск.
            limit: Сколько номеров необходимо зарезервировать.
            skip_golden: Пропускать "золотые" номера (кратные 100).

        Returns:
            list[DocNumber]: Список заблокированных номеров, готовых к резервированию.
        """
        stmt = (
            select(DocNumber)
            .where(
                DocNumber.status == DocNumStatus.released,
                DocNumber.numeric >= base_start,
            )
            .order_by(DocNumber.numeric.asc())
            .with_for_update(skip_locked=True)
            .limit(limit * 2)   # Берем с запасом на случай отбраковки золотых номеров
        )

        result = await self.session.execute(stmt)
        numbers = result.scalars().all()

        if skip_golden:
            numbers = [n for n in numbers if n.numeric % 100 != 0]

        return numbers[:limit]

    async def reserve_existing(
        self,
        numbers: list[DocNumber],
        user_id: int,
        session_id: str,
        ttl_seconds: int,
    ) -> list[int]:
        """
        Резервирует уже существующие в базе (ранее освобождённые) номера.

        Returns:
            list[int]: Список numeric успешно зарезервированных номеров.
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=ttl_seconds)
        reserved = []

        for number in numbers:
            await self.session.execute(
                update(DocNumber)
                .where(DocNumber.id == number.id)
                .values(
                    status=DocNumStatus.reserved,
                    reserved_by=user_id,
                    session_id=session_id,
                    reserved_at=now,
                    expires_at=expires_at,
                    released_at=None,
                )
            )
            await self.session.flush()
            reserved.append(number.numeric)

        return reserved

    async def create_and_reserve_new(
        self,
        candidates: list[int],
        user_id: int,
        session_id: str,
        ttl_seconds: int,
    ) -> list[int]:
        """
        Создаёт и резервирует новые номера, которых ещё нет в таблице.

        При возникновении `IntegrityError` (параллельная транзакция успела создать номер)
        происходит откат и пропуск конфликтного номера.

        Returns:
            list[int]: Список успешно созданных и зарезервированных номеров.
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=ttl_seconds)
        reserved = []

        for num in candidates:
            dn = DocNumber(
                numeric=num,
                is_golden=(num % 100 == 0),
                status=DocNumStatus.reserved,
                reserved_by=user_id,
                session_id=session_id,
                reserved_at=now,
                expires_at=expires_at,
            )
            self.session.add(dn)

            try:
                await self.session.flush()
                reserved.append(num)
            except IntegrityError:
                await self.session.rollback()
                await self.session.begin()
                continue

        return reserved

    async def reserve_specific_numbers(
        self,
        numbers: list[int],
        user_id: int,
        session_id: str,
        ttl_seconds: int,
    ) -> list[int]:
        """
        Принудительно резервирует конкретные номера, запрошенные пользователем.

        Если номер свободен — резервирует. Если не существует — создаёт и резервирует.
        Занятые номера (assigned/reserved) пропускаются.

        Returns:
            list[int]: Список номеров, которые удалось успешно зарезервировать.
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=ttl_seconds)
        reserved: list[int] = []

        for num in sorted(numbers):
            stmt = select(DocNumber).where(DocNumber.numeric == num).with_for_update()
            row = await self.session.scalar(stmt)

            if row:
                if row.status in (DocNumStatus.assigned, DocNumStatus.reserved):
                    continue

                row.status = DocNumStatus.reserved
                row.reserved_by = user_id
                row.session_id = session_id
                row.reserved_at = now
                row.expires_at = expires_at
                row.released_at = None
                reserved.append(num)
            else:
                dn = DocNumber(
                    numeric=num,
                    is_golden=(num % 100 == 0),
                    status=DocNumStatus.reserved,
                    reserved_by=user_id,
                    session_id=session_id,
                    reserved_at=now,
                    expires_at=expires_at,
                )
                self.session.add(dn)
                reserved.append(num)

        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            await self.session.begin()
            return []

        return reserved

    async def get_reserved_for_session(self, session_id: str) -> list[DocNumber]:
        """Возвращает все номера, зарезервированные в рамках указанной сессии."""
        result = await self.session.execute(
            select(DocNumber)
            .where(
                DocNumber.session_id == session_id,
                DocNumber.status == DocNumStatus.reserved,
            )
            .order_by(DocNumber.numeric.asc())
        )
        return list(result.scalars().all())

    async def mark_assigned(self, numbers: list[int]) -> None:
        """Помечает номера как окончательно присвоенные (зарегистрированные)."""
        now = datetime.utcnow()
        await self.session.execute(
            update(DocNumber)
            .where(DocNumber.numeric.in_(numbers))
            .values(
                status=DocNumStatus.assigned,
                assigned_at=now,
                expires_at=None,
            )
        )

    async def release_session(self, session_id: str) -> int:
        """
        Принудительно освобождает все номера, зарезервированные в указанной сессии.

        Returns:
            int: Количество освобождённых номеров.
        """
        now = datetime.utcnow()
        result = await self.session.execute(
            update(DocNumber)
            .where(
                DocNumber.session_id == session_id,
                DocNumber.status == DocNumStatus.reserved,
            )
            .values(
                status=DocNumStatus.released,
                released_at=now,
                reserved_by=None,
                session_id=None,
                expires_at=None,
            )
            .returning(DocNumber.id)
        )
        return len(result.fetchall())
