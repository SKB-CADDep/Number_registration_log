#!/usr/bin/env python3
"""
Скрипт проверки целостности и качества данных после миграции/импорта.

Выполняет быстрый анализ основных таблиц базы данных:
- Показывает количество записей в таблицах `users`, `equipment`, `documents`
- Выводит последние добавленные записи с примерами
- Используется после запуска импорта из Excel (`import_excel.py`)

Является удобным инструментом для валидации результатов импорта legacy-данных.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH, чтобы можно было импортировать app.*
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text

from app.core.config import settings


def check_data() -> None:
    """
    Выполняет проверку данных в базе после импорта.

    Выводит:
        1. Количество записей в основных таблицах
        2. Примеры последних добавленных пользователей
        3. Примеры последних турбин (оборудования)
        4. Примеры последних зарегистрированных документов

    Использует синхронное подключение к БД (преобразует async URL в sync).
    """
    # Преобразуем асинхронный URL (asyncpg) в синхронный для SQLAlchemy
    db_url = settings.DATABASE_URL.replace("+asyncpg", "")
    engine = create_engine(db_url)

    with engine.connect() as conn:
        print("\n📊 ПРОВЕРКА ДАННЫХ В БД ПОСЛЕ ИМПОРТА")
        print("=" * 70)

        # === Общая статистика ===
        print("\n📈 ОБЩАЯ СТАТИСТИКА:")
        for table in ["users", "equipment", "documents"]:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  Таблица {table:15} → {count:6,} записей")

        print("\n" + "=" * 70)
        print("📝 ПРИМЕРЫ ДАННЫХ:\n")

        # === Последние пользователи ===
        result = conn.execute(text("""
            SELECT username, last_name, first_name, department 
            FROM users 
            ORDER BY id DESC 
            LIMIT 3
        """))
        print("Последние добавленные пользователи:")
        for row in result:
            name = f"{row[1] or ''} {row[2] or ''}".strip()
            department = f"({row[3]})" if row[3] else ""
            print(f"  • {row[0]:20} {name:25} {department}")

        # === Последние турбины ===
        result = conn.execute(text("""
            SELECT factory_no, label, station_object 
            FROM equipment 
            WHERE eq_type = 'Турбина'
            ORDER BY id DESC 
            LIMIT 3
        """))
        print("\nПоследние добавленные турбины:")
        for row in result:
            print(f"  • Зав.№ {row[0]:12} | {row[1]:15} | {row[2] or '—'}")

        # === Последние документы ===
        result = conn.execute(text("""
            SELECT d.numeric, d.doc_name, e.factory_no 
            FROM documents d
            JOIN equipment e ON d.equipment_id = e.id
            ORDER BY d.id DESC 
            LIMIT 3
        """))
        print("\nПоследние зарегистрированные документы:")
        for row in result:
            print(f"  • №{row[0]:06} | {row[1][:35]:35} | Зав.№ {row[2] or '—'}")

        print("\n" + "=" * 70)
        print("✅ Проверка завершена.\n")


if __name__ == "__main__":
    check_data()
