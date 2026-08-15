"""Modelo SQLAlchemy de la tabla `sleep_sessions`."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.sleep_score import SleepScore
    from app.models.user import User


class SleepSession(Base):
    """Una noche de sueno registrada por un usuario.

    Es la entidad central del dominio: el score se calcula sobre ella y las
    metricas de analytics la agregan.
    """

    __tablename__ = "sleep_sessions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Marcas de tiempo sin zona horaria: el dominio del sueno es local por
    # naturaleza ("me acoste a las 23:30"), no un instante absoluto en UTC.
    sleep_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    sleep_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Numero de despertares durante la noche. Entra en el score con peso 30%.
    # server_default se declara con text("0") y no con la cadena "0": la cadena
    # renderiza DEFAULT '0' (literal entrecomillado) mientras que la migracion
    # emite DEFAULT 0. Aunque PostgreSQL almacena lo mismo, la diferencia hace
    # que `alembic revision --autogenerate` detecte un cambio inexistente.
    interruptions: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.timezone("utc", func.now()),
    )

    # -- Relaciones ---------------------------------------------------------
    user: Mapped["User"] = relationship(back_populates="sleep_sessions")

    # Relacion 1:1 con el score. uselist=False la declara como escalar en vez
    # de lista, coherente con la restriccion UNIQUE sobre sleep_scores.session_id.
    score: Mapped["SleepScore | None"] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        uselist=False,
        # lazy="joined" trae el score en la misma consulta que la sesion: el
        # historial y el dashboard siempre necesitan ambos juntos, asi que
        # evita una consulta extra por fila.
        lazy="joined",
    )

    __table_args__ = (
        # Invariantes replicadas desde la capa de servicios. La base de datos
        # es la ultima linea de defensa frente a datos incoherentes.
        CheckConstraint("sleep_end > sleep_start", name="end_after_start"),
        CheckConstraint("interruptions >= 0", name="interruptions_non_negative"),
        CheckConstraint(
            "sleep_end <= sleep_start + INTERVAL '24 hours'",
            name="max_duration",
        ),
        # Indice compuesto para el patron de acceso dominante: sesiones de un
        # usuario ordenadas de mas reciente a mas antigua. El DESC permite que
        # PostgreSQL resuelva el ORDER BY recorriendo el indice, sin ordenar.
        #
        # El orden descendente se expresa con `text()` y no con
        # `sleep_start.desc()`: dentro del cuerpo de la clase, `sleep_start` es
        # todavia un objeto MappedColumn sin resolver, no una Column, y no
        # expone los operadores de ordenacion.
        Index("ix_sleep_sessions_user_id_sleep_start", "user_id", text("sleep_start DESC")),
        Index("ix_sleep_sessions_user_id", "user_id"),
    )

    @property
    def duration_hours(self) -> float:
        """Duracion del sueno en horas decimales.

        Propiedad calculada en Python y no columna persistida: es informacion
        derivada de sleep_start/sleep_end, y almacenarla abriria la puerta a
        que quedara desincronizada.
        """
        return (self.sleep_end - self.sleep_start).total_seconds() / 3600.0

    def __repr__(self) -> str:
        return f"<SleepSession id={self.id} user_id={self.user_id} start={self.sleep_start}>"
