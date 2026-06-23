"""
CLI-скрипт для импорта исторических данных из Excel-файлов.

Предназначен для первоначальной загрузки (миграции) legacy-данных
в систему регистрации номеров. Запускает процесс парсинга Excel-файла
и сохранения документов + оборудования в базу данных.

Использование:
    python -m app.scripts.import_excel run "path/to/file.xlsx"
    или
    typer run "path/to/file.xlsx"
"""

from __future__ import annotations

import asyncio

import typer

from app.core.db import SessionLocal
from app.services.importer import ExcelImporterService


cli = typer.Typer(
    name="import-excel",
    help="Инструмент для импорта исторических данных из Excel",
    add_completion=False,
)


@cli.command()
def run(path: str):
    """
    Запускает импорт данных из указанного Excel-файла (.xlsx).

    Создаёт новую асинхронную сессию БД, инициализирует сервис импорта
    и запускает обработку файла. После завершения выводит статистику импорта.

    Args:
        path: Путь к Excel-файлу, который необходимо импортировать.
              Файл должен соответствовать ожидаемой структуре (см. ExcelImporterService).
    """
    async def _do_import() -> None:
        """
        Внутренняя асинхронная функция, выполняющая импорт.

        Использует контекстный менеджер для корректного закрытия сессии БД.
        """
        async with SessionLocal() as session:
            service = ExcelImporterService(session)
            result = await service.import_file(path)
            print(result)

    asyncio.run(_do_import())


if __name__ == "__main__":
    cli()
