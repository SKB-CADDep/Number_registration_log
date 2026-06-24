"""
Скрипт анализа использования API.

Парсит лог-файл `api_usage.log`, созданный middleware `LogRequestsMiddleware`,
и выводит статистику по частоте вызова эндпоинтов (только успешные ответы 2xx).

Используется для анализа нагрузки, выявления самых популярных эндпоинтов
и мониторинга реального использования системы.

Формат лога, который ожидает скрипт:
    API_CALL method=GET path=/api/v1/documents status_code=200 ...
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path


# Регулярное выражение для парсинга логов API usage
LOG_PATTERN = re.compile(
    r"API_CALL method=(\S+) path=(\S+) status_code=(\d+)"
)


def analyze_logs(log_file: Path = Path("api_usage.log")) -> set[tuple[str, str]] | None:
    """
    Анализирует лог-файл использования API и выводит статистику.

    Подсчитывает количество успешных (2xx) обращений к каждому эндпоинту.
    Выводит результаты в удобном для чтения виде, отсортированные по частоте.

    Args:
        log_file: Путь к файлу лога. По умолчанию ищет `api_usage.log`
                  в корне проекта.

    Returns:
        set[tuple[str, str]] | None: Множество кортежей `(method, path)` для
                                     успешно обработанных запросов, либо None,
                                     если файл не найден или данных нет.
    """
    if not log_file.exists():
        print(f"Ошибка: Файл логов '{log_file}' не найден.")
        return None

    usage_counter = Counter()

    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            match = LOG_PATTERN.search(line)
            if not match:
                continue

            method, path, status_code_str = match.groups()

            # Считаем только успешные ответы (статус 2xx)
            if status_code_str.startswith("2"):
                usage_counter[(method, path)] += 1

    print("\n--- Статистика использования API (успешные вызовы) ---")
    if not usage_counter:
        print("Данных об успешных вызовах API не найдено.\n")
        return None

    print(f"{'Вызовов':<10} {'Метод':<8} Путь")
    print("-" * 60)

    for (method, path), count in usage_counter.most_common():
        print(f"{count:<10} {method:<8} {path}")

    print(f"\nВсего уникальных эндпоинтов: {len(usage_counter)}")
    return set(usage_counter.keys())


if __name__ == "__main__":
    analyze_logs()
