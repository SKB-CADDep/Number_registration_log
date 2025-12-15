from __future__ import annotations

from sqlalchemy import select, and_, or_, distinct
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.equipment import Equipment
from app.models.user import User


class ReportsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def fetch(self, station_objects: list[str] | None, date_from, date_to):
        stmt = (
            select(
                Document.numeric,
                Document.reg_date,
                Document.doc_name,
                Document.note,
                Equipment.eq_type,
                Equipment.factory_no,
                Equipment.order_no,
                Equipment.label,
                Equipment.station_no,
                Equipment.station_object,
                User.last_name,
                User.first_name,
                User.middle_name,
                User.department,
                User.username,
            )
            .join(Equipment, Equipment.id == Document.equipment_id)
            .join(User, User.id == Document.user_id)
        )
        where = []
        if station_objects:
            where.append(Equipment.station_object.in_(station_objects))
        if date_from:
            where.append(Document.reg_date >= date_from)
        if date_to:
            where.append(Document.reg_date <= date_to)
        if where:
            stmt = stmt.where(and_(*where))
        stmt = stmt.order_by(Document.reg_date.asc(), Document.numeric.asc())
        res = await self.session.execute(stmt)
        return res.fetchall()

    async def fetch_extended(self, station_objects: list[str] | None, station_no: str | None, label: str | None,
                             factory_no: str | None, order_no: str | None, date_from, date_to, doc_name: str | None,
                             username: str | None, department: str | None):
        stmt = (
            select(
                Document.numeric, Document.reg_date, Document.doc_name, Document.note,
                Equipment.eq_type, Equipment.factory_no, Equipment.order_no,
                Equipment.label, Equipment.station_no, Equipment.station_object,
                User.username, User.department,
            )
            .join(Equipment, Equipment.id == Document.equipment_id)
            .join(User, User.id == Document.user_id)
        )
        where = []
        if station_objects:
            station_object_conditions = [Equipment.station_object.ilike(f"%{so}%") for so in station_objects]
            where.append(or_(*station_object_conditions))
        if label: where.append(Equipment.label.ilike(f"%{label}%"))
        if doc_name: where.append(Document.doc_name.ilike(f"%{doc_name}%"))
        
        # Фильтры
        if username: where.append(User.username.ilike(f"%{username}%"))
        if department: where.append(User.department == department)

        if station_no: where.append(Equipment.station_no == station_no)
        if factory_no: where.append(Equipment.factory_no == factory_no)
        if order_no: where.append(Equipment.order_no.ilike(f"%{order_no}%"))

        if date_from: where.append(Document.reg_date >= date_from)
        if date_to: where.append(Document.reg_date <= date_to)
        if where: stmt = stmt.where(and_(*where))

        stmt = stmt.order_by(Document.reg_date.desc(), Document.numeric.desc())

        res = await self.session.execute(stmt)
        return res.fetchall()

    async def fetch_extended_admin(self, station_objects: list[str] | None, station_no: str | None, label: str | None,
                                   factory_no: str | None, order_no: str | None, username: str | None, date_from,
                                   date_to, eq_type: str | None, doc_name: str | None):
        stmt = (
            select(
                Document.id, Document.numeric, Document.reg_date, Document.doc_name, Document.note,
                Equipment.id.label('eq_id'),
                Equipment.eq_type, Equipment.factory_no, Equipment.order_no,
                Equipment.label, Equipment.station_no, Equipment.station_object,
                User.username,
            )
            .join(Equipment, Equipment.id == Document.equipment_id)
            .join(User, User.id == Document.user_id)
        )

        where = []

        if station_objects:
            station_object_conditions = [Equipment.station_object.ilike(f"%{so}%") for so in station_objects]
            where.append(or_(*station_object_conditions))
        if label: where.append(Equipment.label.ilike(f"%{label}%"))
        if username: where.append(User.username.ilike(f"%{username}%"))
        if doc_name: where.append(Document.doc_name.ilike(f"%{doc_name}%"))

        if station_no: where.append(Equipment.station_no == station_no)
        if factory_no: where.append(Equipment.factory_no == factory_no)
        if order_no: where.append(Equipment.order_no.ilike(f"%{order_no}%"))

        if date_from: where.append(Document.reg_date >= date_from)
        if date_to: where.append(Document.reg_date <= date_to)
        if eq_type: where.append(Equipment.eq_type == eq_type)

        if where: stmt = stmt.where(and_(*where))

        stmt = stmt.order_by(Document.reg_date.desc(), Document.numeric.desc())

        res = await self.session.execute(stmt)
        return res.fetchall()

    async def get_all_departments(self) -> list[str]:
        """Получить список всех уникальных отделов."""
        stmt = select(User.department).where(User.department.is_not(None)).distinct().order_by(User.department)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())