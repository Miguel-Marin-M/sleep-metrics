"""Anade la marca is_demo a users para las cuentas de demostracion

Revision ID: 0002_add_is_demo_to_users
Revises: 0001_initial_schema
Create Date: 2026-08-15

Soporta el endpoint POST /auth/demo, que crea una cuenta desechable y sembrada
por cada visitante que quiere probar la aplicacion sin registrarse.

La columna se anade con server_default 'false' y NOT NULL en una sola
operacion: PostgreSQL rellena las filas existentes con el valor por defecto sin
necesidad de un backfill manual en tres pasos. Es seguro incluso con la tabla
poblada, porque desde PostgreSQL 11 anadir una columna con DEFAULT no reescribe
la tabla entera.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# Identificadores de la revision.
revision: str = "0002_add_is_demo_to_users"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Anade la columna is_demo y su indice parcial."""
    op.add_column(
        "users",
        sa.Column(
            "is_demo",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )

    # Indice PARCIAL: solo indexa las filas donde is_demo es verdadero.
    #
    # La columna esta muy sesgada (casi todas las cuentas son reales) y solo se
    # consulta para localizar las de demostracion. Un indice completo incluiria
    # todas las cuentas reales, ocupando espacio y encareciendo cada alta sin
    # aportar nada. El parcial contiene unicamente el conjunto que recorren la
    # purga por caducidad y el control del tope de cuentas vivas.
    op.create_index(
        "ix_users_is_demo",
        "users",
        ["is_demo"],
        postgresql_where=sa.text("is_demo"),
    )


def downgrade() -> None:
    """Elimina el indice y la columna."""
    op.drop_index("ix_users_is_demo", table_name="users")
    op.drop_column("users", "is_demo")
