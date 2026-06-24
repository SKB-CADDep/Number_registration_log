#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт миграции legacy-данных из Excel в PostgreSQL.

Выполняет полную загрузку исторических данных:
- Пользователи (из файла СКБт)
- Оборудование (турбины и вспомогательное)
- Документы (регистрационные номера до ~20к)

Особенности миграции:
- Нормализация и очистка заводских номеров, номеров заказов
- Обработка плейсхолдера "00000" / "0"
- Обновление номеров заказов по справочному листу
- Сдвиг глобального счётчика номеров после импорта
- Защита от дублирования записей

Запуск:
    poetry run python scripts/migrate_data.py
"""

import os
import re
import sys
import logging
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
from sqlalchemy import create_engine, select, text, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

# Добавляем корень проекта в PYTHONPATH
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Импорт моделей
from app.models.user import User
from app.models.equipment import Equipment
from app.models.document import Document

# ====================== Настройка логирования ======================

log_file = project_root / "scripts" / "migration.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


def resolve_db_url() -> str:
    """
    Возвращает синхронный URL базы данных для SQLAlchemy.

    Приоритет:
        1. DATABASE_URL (с заменой +asyncpg → +psycopg2)
        2. Переменные POSTGRES_*
    """
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url.replace("+asyncpg", "")

    host = os.getenv("POSTGRES_SERVER") or os.getenv("POSTGRES_HOST") or "localhost"
    port = os.getenv("POSTGRES_PORT") or "5432"
    user = os.getenv("POSTGRES_USER")
    pwd = os.getenv("POSTGRES_PASSWORD")
    db = os.getenv("POSTGRES_DB")

    if not all([user, pwd, db]):
        raise RuntimeError(
            "Не удалось определить параметры подключения к БД. "
            "Установите DATABASE_URL или POSTGRES_USER/PASSWORD/DB."
        )

    return f"postgresql+psycopg2://{user}:{pwd}@{host}:{port}/{db}"


def normalize_int_str(value: object) -> str:
    """Приводит значение из Excel к чистой строке с целым числом."""
    s = str(value).strip()
    if not s or s.lower() in ("nan", "none", "null"):
        return ""

    try:
        f = float(s)
        if f.is_integer():
            return str(int(f))
    except Exception:
        pass

    m = re.search(r"\d+", s)
    return m.group(0) if m else ""


def normalize_factory_no(value: object) -> str:
    """Нормализует заводской номер. Пустые и нулевые значения → '00000'."""
    s = normalize_int_str(value)
    return "00000" if s in ("", "0") else s


def load_users(session: Session, path: str) -> None:
    """Загружает пользователей из Excel-файла."""
    logger.info(f"Загрузка пользователей из {path}")

    df = pd.read_excel(path, dtype=str, engine="xlrd").fillna("")
    col_map = {
        "Имя пользователя": "username",
        "Фамилия": "last_name",
        "Имя": "first_name",
        "Отчество": "middle_name",
        "Отдел": "department",
    }
    df = df.rename(columns=col_map)

    for col in ["username", "last_name", "first_name", "middle_name", "department"]:
        if col not in df.columns:
            df[col] = ""

    df["username"] = df["username"].str.strip().str.lower()

    records = df[["username", "last_name", "first_name", "middle_name", "department"]].to_dict("records")

    # Добавляем технического пользователя для миграции
    records.append({
        "username": "migration_user",
        "last_name": "System",
        "first_name": "Migration",
        "middle_name": "",
        "department": "IT",
    })

    if not records:
        logger.warning("Нет пользователей для вставки")
        return

    stmt = insert(User).values(records).on_conflict_do_nothing(index_elements=["username"])
    res = session.execute(stmt)
    session.commit()
    logger.info(f"Пользователи: обработано {len(records)}, вставлено {res.rowcount}")


def build_orders_map_from_excel(xlsx_path: str) -> Dict[str, str]:
    """
    Создаёт mapping: последние 5 цифр номера заказа → полный номер заказа.
    Используется для корректного заполнения поля `order_no` в оборудовании.
    """
    xl = pd.ExcelFile(xlsx_path)
    sheet = next((s for s in xl.sheet_names if "заказ" in s.lower()), None)
    if not sheet:
        logger.warning("Лист с номерами заказов не найден")
        return {}

    df = xl.parse(sheet, dtype=str).fillna("")
    col = next((c for c in df.columns if "заказ" in c.lower()), None)
    if not col:
        logger.warning("Колонка с номером заказа не найдена")
        return {}

    df = df.rename(columns={col: "order_no"})

    orders: Dict[str, str] = {}
    pat = re.compile(r"(\d{5})\D*$")

    for _, r in df.iterrows():
        order = str(r.get("order_no", "")).strip()
        if not order:
            continue
        m = pat.search(order)
        if m:
            last5 = m.group(1)
            if last5 != "00000":
                orders[last5] = order

    return orders


def update_order_numbers(session: Session, xlsx_path: str, overwrite_incorrect: bool = True) -> Tuple[int, int]:
    """
    Обновляет поле `order_no` в таблице equipment на основе справочника заказов.

    Returns:
        (updated, cleaned) — количество обновлённых и очищенных записей.
    """
    orders = build_orders_map_from_excel(xlsx_path)
    if not orders:
        return (0, 0)

    updated = 0
    for last5, full_order in orders.items():
        res = session.execute(
            text("UPDATE equipment SET order_no = :order WHERE factory_no = :last5"),
            {"order": full_order, "last5": last5},
        )
        updated += res.rowcount

    cleaned = 0
    if overwrite_incorrect:
        res = session.execute(text("""
            UPDATE equipment
            SET order_no = NULL
            WHERE order_no IS NOT NULL
              AND substring(order_no from '(\d{5})\D*$') <> factory_no
        """))
        cleaned = res.rowcount

    session.commit()
    logger.info(f"Обновлено номеров заказов: {updated}, очищено некорректных: {cleaned}")
    return (updated, cleaned)


def unify_placeholder_equipment(session: Session) -> Tuple[int, int]:
    """
    Объединяет плейсхолдеры оборудования '0' и '00000'.
    Переносит все документы с equipment_id='0' на '00000' и удаляет дубликат.
    """
    id_00000 = session.execute(
        select(Equipment.id).where(Equipment.factory_no == "00000")
    ).scalar_one_or_none()

    id_zero = session.execute(
        select(Equipment.id).where(Equipment.factory_no == "0")
    ).scalar_one_or_none()

    if not id_zero:
        return (0, 0)

    if not id_00000:
        session.execute(text("UPDATE equipment SET factory_no='00000' WHERE id=:id"), {"id": id_zero})
        session.commit()
        return (0, 0)

    # Переносим документы и сессии на корректный плейсхолдер
    res = session.execute(
        text("UPDATE documents SET equipment_id=:to_id WHERE equipment_id=:from_id"),
        {"to_id": id_00000, "from_id": id_zero}
    )
    docs_relinked = res.rowcount or 0

    try:
        session.execute(
            text("UPDATE sessions SET equipment_id=:to_id WHERE equipment_id=:from_id"),
            {"to_id": id_00000, "from_id": id_zero}
        )
    except Exception:
        pass  # таблицы sessions может ещё не быть

    session.execute(text("DELETE FROM equipment WHERE id=:id"), {"id": id_zero})
    session.commit()

    return (docs_relinked, 1)


def load_equipment(session: Session, path: str) -> None:
    """Загружает оборудование (турбины) из Excel."""
    logger.info(f"Загрузка оборудования из {path}")

    df = pd.read_excel(path, sheet_name="Турбины УТЗ", dtype=str).fillna("")
    df = df.rename(columns={
        "Зав№": "factory_no",
        "Маркировка турбины": "label",
        "Наименование станции": "station_object",
        "Станц. №": "station_no",
    })

    df["factory_no"] = df["factory_no"].map(normalize_factory_no)
    df["eq_type"] = "Турбина"
    df = df.drop_duplicates(subset=["factory_no"])

    existing_fns = {fn for (fn,) in session.execute(select(Equipment.factory_no)).all() if fn}

    eq_records = []
    for _, r in df.iterrows():
        fn = (r.get("factory_no") or "").strip()
        if not fn or fn in existing_fns:
            continue
        eq_records.append({
            "factory_no": fn,
            "label": r.get("label") or None,
            "station_object": r.get("station_object") or None,
            "station_no": r.get("station_no") or None,
            "eq_type": "Турбина",
            "notes": None,
        })

    # Создаём плейсхолдер, если его нет
    if "00000" not in existing_fns and not any(x["factory_no"] == "00000" for x in eq_records):
        eq_records.append({
            "factory_no": "00000",
            "eq_type": "Вспомогательное оборудование",
            "label": "General/Unlinked",
            "notes": "Auto-created placeholder for documents without equipment",
        })

    if eq_records:
        res = session.execute(insert(Equipment).values(eq_records))
        session.commit()
        logger.info(f"Оборудование: обработано {len(df)}, вставлено {res.rowcount or 0}")

    updated, cleaned = update_order_numbers(session, path, overwrite_incorrect=True)
    docs_relinked, eq_deleted = unify_placeholder_equipment(session)

    if docs_relinked or eq_deleted:
        logger.info(f"Объединение плейсхолдеров: документов перенесено = {docs_relinked}, удалено записей = {eq_deleted}")


def load_documents(session: Session, path: str) -> None:
    """Загружает документы (регистрационные номера) из Excel."""
    logger.info(f"Загрузка документов из {path}")

    df = pd.read_excel(path, dtype=str).fillna("")

    existing_nums = {n for (n,) in session.execute(select(Document.numeric)).all()}
    eq_cache: Dict[str, int] = {
        fn: eid for (eid, fn) in session.execute(select(Equipment.id, Equipment.factory_no)).all() if fn
    }

    default_user_id = session.execute(
        select(User.id).where(User.username == "migration_user")
    ).scalar_one_or_none()

    if not default_user_id:
        raise RuntimeError("Пользователь 'migration_user' не найден в базе")

    to_add = []
    skipped = 0
    virtual_eq_created = 0

    for _, row in df.iterrows():
        designation = str(row.get("Обозначение", "")).strip()
        m = re.search(r"(\d+)", designation)
        if not m:
            skipped += 1
            continue

        numeric = int(m.group(1))
        if numeric in existing_nums:
            skipped += 1
            continue

        doc_name = str(row.get("Наименование", "")).strip() or f"DOC-{numeric}"
        note = str(row.get("Примечание", "")).strip() or None

        factory_no = normalize_int_str(row.get("Зав.№ турбины первичного применения", ""))

        eq_id = eq_cache.get(factory_no) if factory_no and factory_no != "00000" else None
        if not eq_id:
            eq_id = eq_cache.get("00000")
            if not eq_id:
                virt_no = f"VIRT-DOC-{numeric}"
                if virt_no not in eq_cache:
                    veq = Equipment(
                        eq_type="Вспомогательное оборудование",
                        factory_no=virt_no,
                        label=f"Virtual for {doc_name}",
                        notes=f"Created automatically for document #{numeric}",
                    )
                    session.add(veq)
                    session.flush()
                    eq_cache[virt_no] = veq.id
                    virtual_eq_created += 1
                eq_id = eq_cache[virt_no]

        to_add.append({
            "numeric": numeric,
            "doc_name": doc_name,
            "note": note,
            "equipment_id": eq_id,
            "user_id": default_user_id,
        })

    if to_add:
        stmt = insert(Document).values(to_add).on_conflict_do_nothing()
        res = session.execute(stmt)
        session.commit()
        logger.info(
            f"Документы: подготовлено {len(to_add)}, вставлено {res.rowcount or 0}, "
            f"пропущено {skipped}, создано виртуального оборудования: {virtual_eq_created}"
        )
    else:
        logger.info("Нет новых документов для загрузки")


def bump_counter_after_import(session: Session) -> int:
    """Устанавливает счётчик номеров после импорта, избегая «золотых» номеров."""
    max_num = session.execute(select(func.max(Document.numeric))).scalar()
    if not max_num:
        return 0

    next_start = int(max_num) + 1
    if next_start % 100 == 0:           # избегаем золотых номеров
        next_start += 1

    session.execute(text("""
        INSERT INTO doc_counter (id, base_start, next_normal_start)
        VALUES (1, :n, :n)
        ON CONFLICT (id) DO UPDATE
        SET base_start = EXCLUDED.base_start,
            next_normal_start = EXCLUDED.next_normal_start
    """), {"n": next_start})

    session.commit()
    logger.info(f"Счётчик номеров установлен на {next_start}")
    return next_start


def main() -> int:
    """Основная функция миграции."""
    files = {
        "users": project_root / "data" / "Копия Актуальный список пользователей СКБт.xls",
        "equipment": project_root / "data" / "Копия Паровые Турбины.xlsx",
        "documents": project_root / "data" / "Копия Номера до 20к.xlsx",
    }

    for name, filepath in files.items():
        if not filepath.exists():
            print(f"ОШИБКА: файл не найден: {filepath}")
            return 1

    db_url = resolve_db_url()
    engine = create_engine(db_url, pool_pre_ping=True)

    with Session(engine) as session:
        load_users(session, str(files["users"]))
        load_equipment(session, str(files["equipment"]))
        load_documents(session, str(files["documents"]))
        bump_counter_after_import(session)

    print("\nМиграция успешно завершена!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
