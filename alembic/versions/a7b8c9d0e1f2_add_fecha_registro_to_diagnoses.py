"""add fecha_registro to diagnoses

Revision ID: a7b8c9d0e1f2
Revises: f6dacd00ddbe
Create Date: 2026-06-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, None] = 'f6dacd00ddbe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Agregar la columna como nullable para no romper filas existentes.
    op.add_column('diagnoses', sa.Column('fecha_registro', sa.DateTime(), nullable=True))
    # 2) Backfill: para diagnósticos previos usamos su fecha de diagnóstico.
    op.execute("UPDATE diagnoses SET fecha_registro = fecha_diagnostico WHERE fecha_registro IS NULL")
    # 3) Forzar NOT NULL una vez poblada.
    op.alter_column('diagnoses', 'fecha_registro', existing_type=sa.DateTime(), nullable=False)


def downgrade() -> None:
    op.drop_column('diagnoses', 'fecha_registro')
