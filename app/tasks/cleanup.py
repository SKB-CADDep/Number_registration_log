"""
Модуль фоновых задач очистки (Cleanup Tasks).

Отвечает за периодическое удаление просроченных сессий резервирования
и освобождение номеров, которые были зарезервированы, но не использованы.

Использует APScheduler для запуска задачи каждые 60 секунд.
Содержит защитные механизмы на случай, если таблицы ещё не созданы
(например, при первом запуске приложения).
"""

from __future__ import annotations

from datetime import datetime, timedelta
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.repositories.doc_numbers import DocNumbersRepository
from app.repositories.sessions import SessionsRepository


logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def start_scheduler(session_factory) -> None:
    """
    Запускает планировщик фоновых задач очистки.

    Добавляет задачу `_cleanup_expired`, которая будет выполняться
    каждые 60 секунд. Используется при старте приложения.

    Args:
        session_factory: Фабрика сессий SQLAlchemy (обычно `async_sessionmaker`).
    """
    if scheduler.running:
        logger.warning("Scheduler is already running.")
        return

    scheduler.add_job(
        _cleanup_expired,
        IntervalTrigger(seconds=60),
        args=[session_factory],
        id="cleanup-expired",
        next_run_time=datetime.utcnow() + timedelta(seconds=10),
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started with TTL cleanup job (interval: 60s).")


def stop_scheduler() -> None:
    """Корректно останавливает планировщик APScheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down.")


async def _cleanup_expired(session_factory) -> None:
    """
    Фоновая задача очистки просроченных сессий и номеров.

    Выполняется периодически планировщиком. Проверяет существование
    необходимых таблиц перед запуском логики, чтобы избежать ошибок
    при старте приложения до выполнения миграций.

    Логика:
        1. Пометить просроченные сессии как `expired`.
        2. Освободить номера, связанные с просроченными/отменёнными сессиями.
        3. Зафиксировать изменения.

    Все ошибки логируются, но не прерывают работу планировщика.
    """
    try:
        async with session_factory() as session:
            if not await _tables_exist(session):
                logger.info("TTL cleanup: tables not ready yet, skipping this run.")
                return

            now = datetime.utcnow()

            srepo = SessionsRepository(session)
            nrepo = DocNumbersRepository(session)

            await srepo.expire_old(now)
            await nrepo.release_expired(now)

            await session.commit()
            logger.debug("TTL cleanup job finished successfully.")

    except ProgrammingError as e:
        logger.warning("TTL cleanup skipped (DB not ready): %s", e)
    except Exception:
        logger.exception("TTL cleanup job failed unexpectedly")


async def _tables_exist(session: AsyncSession) -> bool:
    """
    Проверяет существование необходимых таблиц в базе данных.

    Использует PostgreSQL-специфичную функцию `to_regclass()`.
    Возвращает `True` только если обе таблицы (`sessions` и `doc_numbers`)
    уже существуют. Предотвращает ошибки при первом запуске приложения.

    Returns:
        bool: `True`, если обе таблицы существуют.
    """
    q = text(
        "SELECT to_regclass('public.sessions') as s, "
        "to_regclass('public.doc_numbers') as d"
    )
    res = await session.execute(q)
    s, d = res.fetchone() or (None, None)
    return bool(s and d)
