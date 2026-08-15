"""Modelo SQLAlchemy de la tabla `sleep_scores`."""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Numeric,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.sleep_session import SleepSession


class SleepScore(Base):
    """Score de calidad (0-100) calculado para una sesion de sueno.

    Se persiste en lugar de recalcularse siempre al vuelo porque el historial y
    el dashboard necesitan el score de decenas de sesiones en una sola consulta.
    `GET /analytics/score/{session_id}` recalcula y actualiza esta fila, de modo
    que registrar los habitos despues de crear la sesion refresque el resultado.
    """

    __tablename__ = "sleep_scores"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    # UNIQUE ademas de FK: garantiza la relacion 1:1 con la sesion y convierte
    # el recalculo en un UPDATE en lugar de acumular filas historicas.
    session_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("sleep_sessions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    # NUMERIC(5,2) y no FLOAT: los decimales binarios no representan valores
    # como 87.55 de forma exacta y acabarian mostrandose con ruido en la UI.
    score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)

    calculated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.timezone("utc", func.now()),
    )

    # -- Relaciones ---------------------------------------------------------
    session: Mapped["SleepSession"] = relationship(back_populates="score")

    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="range"),
        Index("ix_sleep_scores_session_id", "session_id"),
    )

    def __repr__(self) -> str:
        return f"<SleepScore session_id={self.session_id} score={self.score}>"
