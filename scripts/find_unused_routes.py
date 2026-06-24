#!/usr/bin/env python3
"""
Скрипт поиска неиспользуемых эндпоинтов.

Сравнивает все маршруты, зарегистрированные в FastAPI-приложении,
с данными из лога использования (api_usage.log) и выводит список
эндпоинтов, которые ни разу не были вызваны.

Полезен для поиска мёртвого кода и анализа реального использования API.
"""

from __future__ import annotations

from fastapi.routing import APIRoute
from pathlib import Path

from app.main import app
from scripts.analyze_api_usage import analyze_logs


def get_all_defined_routes() -> set[tuple[str, str]]:
    """
    Возвращает множество всех маршрутов, определённых в приложении.

    Исключает технические маршруты документации (/docs, /redoc, /openapi.json).
    """
    routes = set()

    for route in app.routes:
        if isinstance(route, APIRoute):
            if route.path in ("/docs", "/redoc", "/openapi.json"):
                continue
            for method in sorted(route.methods):
                routes.add((method, route.path))

    return routes


def main() -> None:
    """
    Основная функция скрипта.
    """
    print("Анализ неиспользуемых маршрутов...\n")

    all_defined_routes = get_all_defined_routes()
    used_routes = analyze_logs(Path("api_usage.log"))

    if used_routes is None:
        print("Ошибка: Не удалось прочитать лог-файл api_usage.log")
        exit(1)

    unused_routes = all_defined_routes - used_routes

    print("\n" + "=" * 80)
    print("НЕИСПОЛЬЗУЕМЫЕ ЭНДПОИНТЫ (кандидаты на удаление)")
    print("=" * 80)

    if not unused_routes:
        print("Все определённые эндпоинты были использованы.")
    else:
        print(f"Найдено неиспользуемых маршрутов: {len(unused_routes)}\n")
        print(f"{'Метод':<8} Путь")
        print("-" * 70)
        for method, path in sorted(unused_routes):
            print(f"{method:<8} {path}")

    print("\n" + "=" * 80)
    print("Рекомендация: перед удалением маршрутов убедитесь, что они")
    print("не используются фронтендом или внешними системами.\n")


if __name__ == "__main__":
    main()
