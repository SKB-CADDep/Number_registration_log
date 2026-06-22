"""
Модуль инициализации базы данных.

Настраивает асинхронное подключение к базе данных через SQLAlchemy 2.0.
Предоставляет движок (Engine), фабрику сессий и FastAPI-зависимость (Dependency) 
для безопасного внедрения сессий БД в обработчики маршрутов (роутеры).
"""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Создание асинхронного движка SQLAlchemy. 
# pool_pre_ping=True обеспечивает автоматическую проверку "живучести" соединения перед его использованием.
engine: AsyncEngine = create_async_engine(settings.database_url, future=True, pool_pre_ping=True)

# Фабрика для создания новых изолированных асинхронных сессий
SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False, autocommit=False)


async def lifespan_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI Dependency: Провайдер асинхронной сессии базы данных.

    Создает новую сессию для каждого входящего HTTP-запроса и гарантированно 
    закрывает её после завершения обработки запроса (благодаря блоку async with).
    Используется в эндпоинтах через `Depends(lifespan_session)`.

    Yields:
        AsyncSession: Активная асинхронная сессия подключения к БД.
    """
    async with SessionLocal() as session:
        yield session
