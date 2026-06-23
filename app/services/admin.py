"""
Модуль административного сервиса.

Содержит бизнес-логику, доступную только администраторам системы.
В текущей версии отвечает за генерацию предложений «золотых» номеров
(номеров, кратных 100), которые можно зарезервировать для особых случаев.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.counter import CounterRepository
from app.repositories.doc_numbers import DocNumbersRepository
from app.utils.numbering import is_golden


class AdminService:
    """
    Сервис административных операций.

    Предоставляет методы, которые требуют повышенных привилегий:
    - генерация списка доступных «золотых» номеров
    - (в будущем) другие административные действия

    Использует репозитории `CounterRepository` и `DocNumbersRepository`
    для работы со счётчиком и состоянием номеров.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация сервиса с необходимыми репозиториями."""
        self.session = session
        self.counter_repo = CounterRepository(session)
        self.numbers_repo = DocNumbersRepository(session)

    async def suggest_golden(self, limit: int = 10) -> list[int]:
        """
        Возвращает список предложенных «золотых» номеров (кратных 100),
        доступных для резервирования.

        Логика работы:
            1. Получает текущее значение счётчика с блокировкой (`FOR UPDATE`).
            2. Вычисляет ближайший «золотой» номер (кратный 100).
            3. Запрашивает все существующие золотые номера >= базового значения.
            4. Исключает уже зарезервированные или назначенные номера.
            5. Генерирует кандидаты, пропуская занятые номера.

        Примечание: поскольку в таблице `doc_numbers` хранятся только номера,
        которые когда-либо появлялись в системе, отсутствие записи = номер свободен.

        Args:
            limit: Максимальное количество предлагаемых номеров (по умолчанию 10).

        Returns:
            list[int]: Список «золотых» номеров, доступных для резервирования,
                       отсортированных по возрастанию.
        """
        counter = await self.counter_repo.get_for_update()
        base = counter.base_start

        # Находим ближайший золотой номер (кратный 100)
        start = ((max(counter.next_normal_start, base) + 99) // 100) * 100

        # Получаем все золотые номера, которые уже были использованы или зарезервированы
        existing_reserved_or_assigned = set()

        # Локальный импорт оставлен, чтобы избежать циклических зависимостей
        from sqlalchemy import select
        from app.models.doc_number import DocNumber, DocNumStatus

        res = await self.session.execute(
            select(DocNumber.numeric, DocNumber.status)
            .where(
                DocNumber.numeric >= base,
                DocNumber.is_golden.is_(True),
            )
        )
        for numeric, status in res.fetchall():
            if status in (DocNumStatus.assigned, DocNumStatus.reserved):
                existing_reserved_or_assigned.add(numeric)

        # Формируем список доступных золотых номеров
        candidates = []
        cur = start
        while len(candidates) < limit:
            if is_golden(cur) and cur not in existing_reserved_or_assigned:
                candidates.append(cur)
            cur += 100

        return candidates
