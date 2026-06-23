"""
Модуль бизнес-логики формирования отчетов и выгрузок.

Отвечает за получение отфильтрованных данных о документах для:
- Отображения в таблицах на фронтенде (JSON)
- Экспорта в Excel
- Административного поиска документов с целью их редактирования

Содержит три уровня детализации отчётов:
- Базовый (`get_rows`)
- Расширенный (`get_rows_extended`)
- Административный (`get_rows_extended_admin`)
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.reports import ReportsRepository
from app.utils.numbering import format_doc_no
from app.utils.excel import ReportExcelBuilder


class ReportsService:
    """
    Сервис формирования отчетов и аналитики.

    Предоставляет методы для получения данных с различной глубиной детализации
    и подготовки их для отображения или экспорта в Excel. Все методы делегируют
    построение SQL-запросов репозиторию `ReportsRepository`.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Инициализация сервиса."""
        self.session = session
        self.repo = ReportsRepository(session)

    async def get_departments(self) -> list[str]:
        """
        Возвращает список всех уникальных отделов, встречающихся в документах.

        Используется для построения фильтров на фронтенде.
        """
        return await self.repo.get_all_departments()

    async def get_rows(
        self,
        station_objects: list[str] | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ):
        """
        Базовый метод получения строк отчёта (устаревающий).

        Возвращает данные в формате, включающем ФИО пользователя по отдельности.
        Используется только для старого экспорта в Excel.

        Рекомендуется использовать `get_rows_extended()` в новых разработках.
        """
        rows = await self.repo.fetch(station_objects, date_from, date_to)
        payload = []
        for (
            numeric,
            reg_date,
            doc_name,
            note,
            eq_type,
            factory_no,
            order_no,
            label,
            station_no,
            station_object,
            last_name,
            first_name,
            middle_name,
            department,
            username,
        ) in rows:
            payload.append(
                {
                    "doc_no": format_doc_no(numeric),
                    "reg_date": reg_date,
                    "doc_name": doc_name,
                    "note": note,
                    "eq_type": eq_type,
                    "factory_no": factory_no,
                    "order_no": order_no,
                    "label": label,
                    "station_no": station_no,
                    "station_object": station_object,
                    "last_name": last_name,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "department": department,
                    "username_fallback": username
                    if not any([last_name, first_name, middle_name, department])
                    else None,
                }
            )
        return payload

    async def get_rows_extended(
        self,
        station_objects: list[str] | None,
        station_no: str | None,
        label: str | None,
        factory_no: str | None,
        order_no: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        doc_name: str | None = None,
        username: str | None = None,
        department: str | None = None,
    ) -> list[dict]:
        """
        Расширенный поиск документов с поддержкой множества фильтров.

        Основной метод, используемый фронтендом для отображения таблицы отчётов.
        Возвращает данные в формате, готовом для `ReportRowOut`.

        Args:
            station_objects: Список объектов подстанций.
            station_no, label, factory_no, order_no, doc_name: Фильтры по оборудованию и документу.
            date_from, date_to: Период регистрации.
            username: Логин пользователя.
            department: Отдел пользователя.

        Returns:
            list[dict]: Список строк отчёта в формате, подходящем для Pydantic-модели `ReportRowOut`.
        """
        rows = await self.repo.fetch_extended(
            station_objects=station_objects,
            station_no=station_no,
            label=label,
            factory_no=factory_no,
            order_no=order_no,
            date_from=date_from,
            date_to=date_to,
            doc_name=doc_name,
            username=username,
            department=department,
        )

        payload = []
        for (
            numeric,
            reg_date,
            doc_name,
            note,
            eq_type,
            factory_no,
            order_no,
            label,
            station_no,
            station_object,
            username,
            dept_val,  # department из базы
        ) in rows:
            payload.append(
                {
                    "doc_no": format_doc_no(numeric),
                    "numeric": numeric,
                    "reg_date": reg_date.strftime("%d.%m.%Y %H:%M") if reg_date else "",
                    "doc_name": doc_name,
                    "note": note,
                    "eq_type": eq_type,
                    "factory_no": factory_no,
                    "order_no": order_no,
                    "label": label,
                    "station_no": station_no,
                    "station_object": station_object,
                    "username": username,
                    "department": dept_val,
                }
            )
        return payload

    async def export_excel(
        self,
        station_objects: list[str] | None,
        date_from: datetime | None,
        date_to: datetime | None,
    ) -> str:
        """
        Формирует Excel-файл с базовым отчётом (устаревший метод).

        Использует `get_rows()` и старый билдер отчёта.
        """
        data = await self.get_rows(station_objects, date_from, date_to)
        builder = ReportExcelBuilder()
        path = builder.build_report(data)
        return path

    async def export_excel_extended(
        self,
        station_objects: list[str] | None,
        station_no: str | None,
        label: str | None,
        factory_no: str | None,
        order_no: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        doc_name: str | None = None,
        username: str | None = None,
        department: str | None = None,
    ) -> str:
        """
        Формирует Excel-файл с расширенными фильтрами.

        Основной метод экспорта, используемый в текущей версии приложения.
        """
        data = await self.get_rows_extended(
            station_objects=station_objects,
            station_no=station_no,
            label=label,
            factory_no=factory_no,
            order_no=order_no,
            date_from=date_from,
            date_to=date_to,
            doc_name=doc_name,
            username=username,
            department=department,
        )
        builder = ReportExcelBuilder()
        path = builder.build_report_extended(data)
        return path

    async def get_rows_extended_admin(
        self,
        station_objects: list[str] | None,
        station_no: str | None,
        label: str | None,
        factory_no: str | None,
        order_no: str | None,
        username: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        eq_type: str | None,
        doc_name: str | None = None,
    ) -> list[dict]:
        """
        Расширенный поиск документов для административной панели.

        Возвращает дополнительные технические поля (`id`, `eq_id`, `numeric`),
        необходимые для перехода в режим редактирования документа.
        Доступен только администраторам.
        """
        rows = await self.repo.fetch_extended_admin(
            station_objects=station_objects,
            station_no=station_no,
            label=label,
            factory_no=factory_no,
            order_no=order_no,
            username=username,
            date_from=date_from,
            date_to=date_to,
            eq_type=eq_type,
            doc_name=doc_name,
        )

        payload = []
        for (
            id_,
            numeric,
            reg_date,
            doc_name,
            note,
            eq_id,
            eq_type,
            factory_no,
            order_no,
            label,
            station_no,
            station_object,
            username,
        ) in rows:
            payload.append(
                {
                    "id": id_,
                    "doc_no": format_doc_no(numeric),
                    "numeric": numeric,
                    "reg_date": reg_date.strftime("%d.%m.%Y %H:%M") if reg_date else "",
                    "doc_name": doc_name,
                    "note": note,
                    "eq_id": eq_id,
                    "eq_type": eq_type,
                    "factory_no": factory_no,
                    "order_no": order_no,
                    "label": label,
                    "station_no": station_no,
                    "station_object": station_object,
                    "username": username,
                }
            )
        return payload

    async def export_excel_extended_admin(
        self,
        station_objects: list[str] | None,
        station_no: str | None,
        label: str | None,
        factory_no: str | None,
        order_no: str | None,
        username: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        eq_type: str | None,
        doc_name: str | None = None,
    ) -> str:
        """
        Формирует Excel-файл с административным расширенным отчётом.
        """
        data = await self.get_rows_extended_admin(
            station_objects=station_objects,
            station_no=station_no,
            label=label,
            factory_no=factory_no,
            order_no=order_no,
            username=username,
            date_from=date_from,
            date_to=date_to,
            eq_type=eq_type,
            doc_name=doc_name,
        )
        builder = ReportExcelBuilder()
        path = builder.build_report_extended_admin(data)
        return path


def start_of_week(dt: datetime | None = None) -> datetime:
    """
    Возвращает дату начала текущей недели (понедельник 00:00:00).

    Используется для формирования отчётов "за эту неделю", "за прошлую неделю" и т.п.

    Args:
        dt: Дата, от которой нужно посчитать начало недели.
            Если None — используется текущая дата.

    Returns:
        datetime: Дата понедельника текущей недели в 00:00:00.
    """
    dt = dt or datetime.now()
    monday = dt - timedelta(days=dt.weekday())
    return monday.replace(hour=0, minute=0, second=0, microsecond=0)
