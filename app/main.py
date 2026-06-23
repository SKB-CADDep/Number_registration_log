"""
Главный модуль приложения (entry point).

Настраивает FastAPI-приложение, подключает все роутеры, middleware,
настраивает логирование (включая отдельный логгер для аудита API-запросов)
и управляет жизненным циклом приложения (lifespan).
"""

import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core import db
from app.tasks.cleanup import start_scheduler, stop_scheduler
from app.routers import (
    equipment,
    documents,
    sessions,
    reports,
    suggest,
    admin,
    importer,
    users,
)
from app.middleware.log_requests import LogRequestsMiddleware


# ====================== Логирование ======================

# Основной логгер приложения
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Отдельный логгер для аудита использования API (пишется в файл)
api_usage_logger = logging.getLogger("api_usage")
api_usage_logger.setLevel(logging.INFO)

# Ротация логов: максимум 5 МБ на файл, храним 3 старых файла
handler = RotatingFileHandler(
    "api_usage.log", maxBytes=5 * 1024 * 1024, backupCount=3
)
api_usage_logger.addHandler(handler)
api_usage_logger.propagate = False  # Не дублировать сообщения в основной логгер

logger = logging.getLogger(__name__)


# ====================== Lifespan ======================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Управляет запуском и остановкой приложения.

    При старте:
        - Запускает планировщик очистки просроченных сессий и номеров.

    При остановке:
        - Корректно завершает работу планировщика.
    """
    start_scheduler(db.SessionLocal)
    logger.info("Application startup completed. Scheduler started.")

    yield

    stop_scheduler()
    logger.info("Application shutdown completed. Scheduler stopped.")


# ====================== FastAPI приложение ======================

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Система регистрации и резервирования номеров документов",
    version="1.0.0",
    openapi_url="/api/v1/openapi.json",
    lifespan=lifespan,
)

# ====================== Middleware ======================

# Middleware для логирования всех HTTP-запросов
app.add_middleware(LogRequestsMiddleware)

# CORS (если настроен в .env)
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin).rstrip("/") for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ====================== Роутеры ======================

api_router = APIRouter()

api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(equipment.router, prefix="/equipment", tags=["Equipment"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(suggest.router, prefix="/suggest", tags=["Suggest"])
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])
api_router.include_router(importer.router, prefix="/import", tags=["Import"])

app.include_router(api_router, prefix="/api/v1")


# ====================== Health Check ======================

@app.get("/api/health-check", tags=["Health"])
def health_check():
    """
    Простая health-check эндпоинт.

    Используется для мониторинга доступности приложения
    (Kubernetes, Docker Compose, Nginx и т.д.).
    """
    return {"status": "ok"}
