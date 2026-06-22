"""
Модуль промежуточного программного обеспечения (Middleware) для логирования.

Отвечает за перехват всех входящих HTTP-запросов к приложению, 
измерение времени их выполнения и запись структурированных логов.
Полезно для аудита, мониторинга производительности и аналитики использования API.
"""

import logging
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Создаем специальный логгер, чтобы его вывод можно было легко направить в отдельный файл
logger = logging.getLogger("api_usage")


class LogRequestsMiddleware(BaseHTTPMiddleware):
    """
    Middleware для профилирования и логирования API-запросов.
    Встраивается в общий пайплайн обработки запросов FastAPI/Starlette.
    """

    async def dispatch(self, request: Request, call_next, ) -> Response:
        """
        Перехватывает запрос, замеряет время обработки и логирует результат.

        Логирование происходит после выполнения запроса.
        Время указывается в секундах с точностью до 4 знаков после запятой.

        Args:
            request (Request): Входящий HTTP-запрос.
            call_next (Callable): Функция вызова следующего middleware или обработчика.

        Returns:
            Response: HTTP-ответ, сгенерированный приложением.

        Пример записи в лог:
            API_CALL method=GET path=/api/users status_code=200 duration=0.0421
        """
        start_time = time.time()
        
        # Передача управления дальше по цепочке вызовов
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Логируем в структурированном формате для легкого парсинга системами сбора логов
        logger.info(
            "API_CALL method=%s path=%s status_code=%d duration=%.4f",
            request.method,
            request.url.path,
            response.status_code,
            process_time,
        )
        
        return response
