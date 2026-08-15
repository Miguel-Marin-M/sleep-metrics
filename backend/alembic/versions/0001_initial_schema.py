"""Schema inicial: users, sleep_sessions, daily_habits, sleep_scores

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-15

Crea las cuatro tablas del dominio de SleepMetrics con sus llaves foraneas,
indices y restricciones de integridad.

Los nombres de las restricciones NO son arbitrarios: los produce la convencion
de nombres declarada en `app/models/base.py`. Mantenerlos sincronizados es lo
que permite que `alembic revision --autogenerate` no detecte falsos cambios
comparando estas tablas con los modelos.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# Identificadores de la revision.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Valor por defecto de todas las columnas created_at. Se calcula en el servidor
# de base de datos, no en Python, para que todas las filas usen el mismo reloj
# aunque haya varias instancias del backend desplegadas.
UTC_NOW = sa.text("timezone('utc', now())")


def upgrade() -> None:
    """Crea el schema completo."""

    # -----------------------------------------------------------------------
    # users
    # -----------------------------------------------------------------------
    op.create_table(
        "users",
        # Identity(always=True) genera GENERATED ALWAYS AS IDENTITY: PostgreSQL
        # rechaza cualquier INSERT con un id explicito, de modo que la secuencia
        # nunca puede desincronizarse.
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("email = lower(email)", name="ck_users_email_lowercase"),
    )

    # -----------------------------------------------------------------------
    # sleep_sessions
    # -----------------------------------------------------------------------
    op.create_table(
        "sleep_sessions",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("sleep_start", sa.DateTime(), nullable=False),
        sa.Column("sleep_end", sa.DateTime(), nullable=False),
        sa.Column("interruptions", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_sleep_sessions"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_sleep_sessions_user_id",
            # ON DELETE CASCADE: eliminar un usuario limpia todo su historial
            # sin dejar filas huerfanas.
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("sleep_end > sleep_start", name="ck_sleep_sessions_end_after_start"),
        sa.CheckConstraint(
            "interruptions >= 0",
            name="ck_sleep_sessions_interruptions_non_negative",
        ),
        sa.CheckConstraint(
            "sleep_end <= sleep_start + INTERVAL '24 hours'",
            name="ck_sleep_sessions_max_duration",
        ),
    )

    op.create_index("ix_sleep_sessions_user_id", "sleep_sessions", ["user_id"])

    # Indice compuesto con orden descendente en la segunda columna. Sirve al
    # patron de acceso dominante de la aplicacion ("mis sesiones, de la mas
    # reciente a la mas antigua") permitiendo que PostgreSQL resuelva el
    # ORDER BY recorriendo el indice en lugar de ordenar en memoria.
    op.create_index(
        "ix_sleep_sessions_user_id_sleep_start",
        "sleep_sessions",
        ["user_id", sa.text("sleep_start DESC")],
    )

    # -----------------------------------------------------------------------
    # daily_habits
    # -----------------------------------------------------------------------
    op.create_table(
        "daily_habits",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("caffeine_mg", sa.Integer(), server_default=sa.text("0"), nullable=False),
        # Hora del ultimo consumo de cafeina. NULL-able porque el usuario puede
        # no recordarla; el servicio de scoring aplica entonces un factor de
        # proximidad conservador.
        sa.Column("last_caffeine_time", sa.Time(), nullable=True),
        sa.Column("exercise_minutes", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "screen_time_before_bed_minutes",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_daily_habits"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_daily_habits_user_id",
            ondelete="CASCADE",
        ),
        # Habilita la semantica de upsert de POST /habits.
        sa.UniqueConstraint("user_id", "date", name="uq_daily_habits_user_id_date"),
        sa.CheckConstraint("caffeine_mg >= 0", name="ck_daily_habits_caffeine_non_negative"),
        sa.CheckConstraint(
            "exercise_minutes >= 0 AND exercise_minutes <= 1440",
            name="ck_daily_habits_exercise_range",
        ),
        sa.CheckConstraint(
            "screen_time_before_bed_minutes >= 0 "
            "AND screen_time_before_bed_minutes <= 1440",
            name="ck_daily_habits_screen_time_range",
        ),
    )

    op.create_index("ix_daily_habits_user_id", "daily_habits", ["user_id"])
    op.create_index("ix_daily_habits_date", "daily_habits", ["date"])

    # -----------------------------------------------------------------------
    # sleep_scores
    # -----------------------------------------------------------------------
    op.create_table(
        "sleep_scores",
        sa.Column("id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        # NUMERIC(5,2) y no FLOAT: evita el ruido de la representacion binaria
        # en coma flotante al mostrar valores como 87.55 en la interfaz.
        sa.Column("score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("calculated_at", sa.DateTime(), server_default=UTC_NOW, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_sleep_scores"),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["sleep_sessions.id"],
            name="fk_sleep_scores_session_id",
            ondelete="CASCADE",
        ),
        # UNIQUE fuerza la relacion 1:1 con la sesion: recalcular el score es un
        # UPDATE de esta fila y nunca un INSERT adicional.
        sa.UniqueConstraint("session_id", name="uq_sleep_scores_session_id"),
        sa.CheckConstraint("score >= 0 AND score <= 100", name="ck_sleep_scores_range"),
    )

    op.create_index("ix_sleep_scores_session_id", "sleep_scores", ["session_id"])


def downgrade() -> None:
    """Elimina el schema completo.

    El orden es el inverso al de creacion: no se puede eliminar `users`
    mientras existan tablas que la referencian por llave foranea.
    """
    op.drop_index("ix_sleep_scores_session_id", table_name="sleep_scores")
    op.drop_table("sleep_scores")

    op.drop_index("ix_daily_habits_date", table_name="daily_habits")
    op.drop_index("ix_daily_habits_user_id", table_name="daily_habits")
    op.drop_table("daily_habits")

    op.drop_index("ix_sleep_sessions_user_id_sleep_start", table_name="sleep_sessions")
    op.drop_index("ix_sleep_sessions_user_id", table_name="sleep_sessions")
    op.drop_table("sleep_sessions")

    op.drop_table("users")
