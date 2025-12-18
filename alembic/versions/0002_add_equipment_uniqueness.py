"""Add equipment uniqueness constraint

Revision ID: 0002
Revises: 0001
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0002'
down_revision = '0001_init'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Создаем уникальный индекс на комбинацию полей оборудования
    # Используем LOWER и COALESCE для регистронезависимого сравнения
    op.execute("""
        CREATE UNIQUE INDEX ix_equipment_unique_attributes 
        ON equipment (
            LOWER(COALESCE(station_object, '')), 
            LOWER(COALESCE(station_no, '')), 
            LOWER(COALESCE(label, '')), 
            LOWER(COALESCE(factory_no, ''))
        )
        WHERE station_object IS NOT NULL 
           OR station_no IS NOT NULL 
           OR label IS NOT NULL 
           OR factory_no IS NOT NULL
    """)
    # 1. Добавляем колонки
    op.add_column('users', sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False))
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), server_default='false', nullable=False))

    # 2. Переносим старых админов (ХАРДКОД, т.к. из конфига мы их уже удалили)
    # Список взят из твоего старого конфига
    old_admins = ["vgrubtsov", "yuaalekseeva", "lrshlyogin", "pyagavrilov", "mabaturin"]
    
    # Приводим к нижнему регистру и форматируем для SQL
    formatted_list = "', '".join([u.lower() for u in old_admins])
    
    # Выполняем SQL: обновить флаг is_admin для всех, кто был в списке
    op.execute(f"UPDATE users SET is_admin = true WHERE lower(username) IN ('{formatted_list}')")


def downgrade() -> None:
    op.drop_index('ix_equipment_unique_attributes', table_name='equipment')
