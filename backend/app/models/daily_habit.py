"""Modelo SQLAlchemy de la tabla `daily_habits`."""

from datetime import date as date_type
from datetime import datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Time,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class DailyHabit(Base):
    """Habitos diurnos de un usuario en un dia concreto.

    Alimentan el componente de "consistencia con habitos" del score (30% del
    total). Se asocian a la sesion de sueno cuyo `sleep_start` cae en la misma
    fecha, es decir, la noche que comienza ese dia.
    """

    __tablename__ = "daily_habits"

    id: Mapped[int] = mapped_column(BigInteger, Identity(always=True), primary_key=True)

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Fecha de la NOCHE a la que corresponden estos habitos.
    #
    # No es "la fecha del sleep_start" de la sesion: acostarse a las 00:30 del
    # sabado pertenece a la noche del viernes, porque el cafe y las pantallas
    # que influyeron en ese sueno fueron los del viernes. La regla completa
    # esta en `app.services.night`.
    #
    # `date` colisiona con el tipo `datetime.date`, de ahi el alias date_type en
    # los imports de este modulo.
    date: Mapped[date_type] = mapped_column(Date, nullable=False)

    # Cafeina total del dia en miligramos (una taza de cafe ronda los 95 mg).
    #
    # server_default usa text("0") y no la cadena "0": esta ultima renderiza
    # DEFAULT '0' (literal entrecomillado) frente al DEFAULT 0 que emite la
    # migracion, y esa diferencia puramente sintactica hace que
    # `alembic revision --autogenerate` detecte un cambio que no existe.
    caffeine_mg: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    # Hora del ultimo consumo de cafeina del dia.
    #
    # Columna anadida respecto a la especificacion original del modelo de datos:
    # el algoritmo de scoring debe penalizar la "cafeina tardia", y con solo la
    # cantidad diaria total es imposible saber si se consumio a las 8:00 o a
    # las 22:00, que es justamente el factor determinante. Es NULL-able porque
    # el usuario puede no recordarla; en ese caso el servicio de scoring aplica
    # un factor de proximidad conservador (ver scoring_service).
    last_caffeine_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    exercise_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    # Minutos de uso de pantallas en la hora previa a acostarse.
    screen_time_before_bed_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.timezone("utc", func.now()),
    )

    # -- Relaciones ---------------------------------------------------------
    user: Mapped["User"] = relationship(back_populates="daily_habits")

    __table_args__ = (
        # Un unico registro de habitos por usuario y dia. Es la restriccion que
        # habilita la semantica de upsert de POST /habits: volver a enviar los
        # habitos de un dia actualiza la fila en vez de duplicarla.
        #
        # Se deja SIN nombre explicito a proposito, para que lo genere la
        # convencion de nombres de `models/base.py` (-> uq_daily_habits_user_id_date).
        # La convencion "uq" no incluye el token %(constraint_name)s, asi que un
        # nombre explicito la anularia y produciria un identificador
        # inconsistente con el resto del schema.
        UniqueConstraint("user_id", "date"),
        CheckConstraint("caffeine_mg >= 0", name="caffeine_non_negative"),
        CheckConstraint(
            "exercise_minutes >= 0 AND exercise_minutes <= 1440",
            name="exercise_range",
        ),
        CheckConstraint(
            "screen_time_before_bed_minutes >= 0 AND screen_time_before_bed_minutes <= 1440",
            name="screen_time_range",
        ),
        Index("ix_daily_habits_user_id", "user_id"),
        # Indice sobre `date`: el servicio de analytics agrega por rangos de
        # fecha para las correlaciones habitos/score.
        Index("ix_daily_habits_date", "date"),
    )

    def __repr__(self) -> str:
        return f"<DailyHabit id={self.id} user_id={self.user_id} date={self.date}>"
