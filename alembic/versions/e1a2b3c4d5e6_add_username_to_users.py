"""add username to users

Revision ID: e1a2b3c4d5e6
Revises: d98788e947d9
Create Date: 2026-06-20

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e1a2b3c4d5e6'
down_revision: Union[str, None] = 'd98788e947d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Agregar la columna como nullable para no romper filas existentes.
    op.add_column('users', sa.Column('username', sa.String(length=50), nullable=True))
    # 2) Backfill: usar la parte local del correo como username inicial.
    op.execute("UPDATE users SET username = split_part(correo, '@', 1) WHERE username IS NULL")
    # 3) Resolver posibles duplicados agregando el id.
    op.execute(
        """
        UPDATE users SET username = username || '_' || id_usuario
        WHERE id_usuario IN (
            SELECT id_usuario FROM (
                SELECT id_usuario,
                       ROW_NUMBER() OVER (PARTITION BY username ORDER BY id_usuario) AS rn
                FROM users
            ) t WHERE t.rn > 1
        )
        """
    )
    # 4) Forzar NOT NULL y unicidad.
    op.alter_column('users', 'username', existing_type=sa.String(length=50), nullable=False)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_users_username', table_name='users')
    op.drop_column('users', 'username')
