"""
Модуль репозитория для работы с глобальным счетчиком документов.

Реализует потокобезопасное получение и обновление счетчика для сквозной 
нумерации регистрационных документов. Использует механизм блокировок БД 
(SELECT ... FOR UPDATE), чтобы предотвратить race condition при конкурентной 
регистрации.
"""

from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.counter import DocCounter


class CounterRepository:
    """
    Репозиторий для работы с глобальным счетчиком документов (таблица `doc_counter`).

    Обеспечивает атомарное получение и обновление счетчика. 
    В системе используется singleton-подход — в таблице всегда одна запись с `id = 1`.
    """

    def __init__(self, session: AsyncSession) -> None:
        """
        Инициализация репозитория.

        Args:
            session: Асинхронная сессия SQLAlchemy.
        """
        self.session = session

    async def get_for_update(self) -> DocCounter:
        """
        Возвращает текущий счетчик с эксклюзивной блокировкой строки (`FOR UPDATE`).

        Пока транзакция не завершится (commit/rollback), другие запросы будут ждать.
        Это гарантирует, что два параллельных запроса не получат одинаковый номер.

        Если запись счетчика ещё не существует (первый запуск системы), 
        она будет автоматически создана.

        Returns:
            DocCounter: Объект счетчика, заблокированный для других транзакций.
        """
        result = await self.session.execute(
            select(DocCounter)
            .where(DocCounter.id == 1)
            .with_for_update()
        )
        counter = result.scalars().first()

        # Ленивая инициализация при первом обращении
        if not counter:
            counter = DocCounter(id=1, base_start=1, next_normal_start=1)
            self.session.add(counter)
            await self.session.flush()

        return counter

    async def set_after_import(self, base_start: int) -> None:
        """
        Жёстко обновляет значения счетчика.

        Используется при первичном импорте исторических данных из старых систем,
        чтобы новые регистрационные номера не пересекались с уже существующими.

        Args:
            base_start: Новое базовое значение, от которого будет продолжена нумерация.
        """
        await self.session.execute(
            update(DocCounter)
            .where(DocCounter.id == 1)
            .values(
                base_start=base_start,
                next_normal_start=base_start,
            )
        )
